#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import os
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from retry import retry
from urllib.parse import urljoin

class MCPECrawler:
    """针对 mcpelife.com 的 MCPE资源爬虫"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.data_dir = 'data'
        self.data_file = os.path.join(self.data_dir, 'resources.json')
        self.base_url = 'https://mcpelife.com'
        
        # 定义要爬取的分类路径 (根据网站实际导航调整)
        self.categories = [
            '',  # 首页
            '/mods-addons/',
            '/maps-skins/',
            '/servers/',
            '/guides-tips/'
        ]
        
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_headers(self):
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': self.base_url,
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    @retry(tries=3, delay=2, backoff=2)
    def fetch_page(self, url):
        """获取页面内容（带重试机制）"""
        try:
            full_url = urljoin(self.base_url, url)
            print(f"🌐 正在抓取: {full_url}")
            response = requests.get(
                full_url, 
                headers=self.get_headers(),
                timeout=15
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"❌ 请求失败 {full_url}: {e}")
            raise
    
    def parse_listing_page(self, html):
        """解析列表页，提取资源条目"""
        soup = BeautifulSoup(html, 'lxml')
        resources = []
        
        # TODO: 重要! 需要您根据 mcpelife.com 的实际HTML结构调整以下选择器
        # 例如：文章项可能包含在 <article> 或 <div class="post"> 中
        items = soup.select('article.post')  # 常见博客结构
        if not items:
            items = soup.select('.post-item')  # 另一种常见结构
        if not items:
            items = soup.select('.entry')  # 再试一种
        
        print(f"  找到 {len(items)} 个可能的条目")
        
        for item in items[:15]:  # 每次抓取前15个，避免过多
            try:
                # 提取标题和链接
                title_elem = item.select_one('h2.entry-title a') or item.select_one('.post-title a')
                if not title_elem:
                    continue
                    
                title = title_elem.text.strip()
                post_url = urljoin(self.base_url, title_elem.get('href', ''))
                
                # 提取图片
                img_elem = item.select_one('img')
                img_url = img_elem.get('src') if img_elem else ''
                if img_url and not img_url.startswith('http'):
                    img_url = urljoin(self.base_url, img_url)
                
                # 提取描述
                desc_elem = item.select_one('.entry-summary p') or item.select_one('.post-excerpt')
                description = desc_elem.text.strip() if desc_elem else ''
                
                # 提取分类/标签
                category_elem = item.select_one('.category a') or item.select_one('.post-categories a')
                category = category_elem.text.strip() if category_elem else '未分类'
                
                # 我们需要下载链接，所以需要进入详情页提取
                resource = {
                    'name': title,
                    'url': post_url,
                    'cover_image': img_url or 'https://via.placeholder.com/300x180?text=MCPE',
                    'description': description[:200] + '...' if len(description) > 200 else description,
                    'category': category,
                    'source': 'mcpelife.com',
                    'crawled_at': datetime.now().isoformat(),
                }
                
                resources.append(resource)
                
            except Exception as e:
                print(f"⚠️ 解析条目时出错: {e}")
                continue
        
        return resources
    
    def fetch_download_url(self, post_url):
        """进入文章详情页提取实际的下载链接"""
        try:
            html = self.fetch_page(post_url)
            soup = BeautifulSoup(html, 'lxml')
            
            # TODO: 根据详情页的实际下载按钮/链接调整选择器
            download_link = None
            # 查找常见的下载按钮
            download_elem = soup.select_one('a.download-button') or \
                           soup.select_one('a[href*="download"]') or \
                           soup.select_one('.download-link a')
            
            if download_elem:
                download_link = urljoin(self.base_url, download_elem.get('href', ''))
            
            # 同时尝试提取版本号
            version_elem = soup.select_one('.version') or soup.select_one('.game-version')
            version = version_elem.text.strip() if version_elem else '未知'
            
            return download_link, version
            
        except Exception as e:
            print(f"⚠️ 无法从 {post_url} 提取下载链接: {e}")
            return None, '未知'
    
    def load_existing_data(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def merge_resources(self, new_resources, existing_resources):
        """合并资源，基于URL去重"""
        existing_urls = {r.get('url') for r in existing_resources}
        
        for resource in new_resources:
            if resource.get('url') and resource['url'] not in existing_urls:
                # 进入详情页获取下载链接
                print(f"  获取下载链接: {resource['name']}")
                download_url, version = self.fetch_download_url(resource['url'])
                resource['download_url'] = download_url or '#'
                resource['version'] = version
                
                existing_resources.insert(0, resource)
                time.sleep(random.uniform(1, 3))  # 礼貌性延迟
        
        return existing_resources[:100]  # 最多保留100个
    
    def save_data(self, resources):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(resources, f, ensure_ascii=False, indent=2)
        print(f"✅ 数据已保存，共 {len(resources)} 个资源")
    
    def run(self):
        print("🚀 开始爬取 mcpelife.com ...")
        all_new_resources = []
        
        for category in self.categories:
            try:
                html = self.fetch_page(category)
                resources = self.parse_listing_page(html)
                print(f"  从 {category or '首页'} 获取到 {len(resources)} 个资源")
                all_new_resources.extend(resources)
                
                # 爬取下一页? 这里可以扩展分页逻辑
                
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"❌ 处理分类 {category} 失败: {e}")
                continue
        
        if all_new_resources:
            existing = self.load_existing_data()
            merged = self.merge_resources(all_new_resources, existing)
            self.save_data(merged)
            print(f"✨ 更新完成！新增 {len(all_new_resources)} 个资源")
        else:
            print("⚠️ 本次运行未获取到新资源")

if __name__ == '__main__':
    crawler = MCPECrawler()
    crawler.run()
