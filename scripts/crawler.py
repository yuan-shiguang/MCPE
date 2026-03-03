#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import os
import time
import re
import random
from datetime import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import urljoin

class MCPECrawler:
    """针对 mcpelife.com 的精确爬虫（支持列表页和详情页）"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.data_dir = 'data'
        self.data_file = os.path.join(self.data_dir, 'resources.json')
        self.base_url = 'https://mcpelife.com'
        
        # 从导航栏提取的精确分类链接
        self.category_urls = [
            '/download/',    # Minecraft APK
            '/mods/',        # 模组
            '/servers/',     # 服务器
            '/textures/',    # 纹理
            '/shaders/',     # 着色器
            '/maps/',        # 地图
            '/skins/',       # 皮肤
            '/seeds/',       # 种子
            '/soft/',        # 软
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
    
    def fetch_page(self, url):
        """获取页面内容"""
        full_url = urljoin(self.base_url, url)
        print(f"🌐 正在抓取: {full_url}")
        
        try:
            response = requests.get(
                full_url, 
                headers=self.get_headers(),
                timeout=15
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"❌ 请求失败: {e}")
            return None
    
    def parse_category_page(self, html, category_name):
        """解析分类页面，提取资源列表"""
        soup = BeautifulSoup(html, 'lxml')
        resources = []
        
        # 精确选择器：每个资源条目都在 article.col-md-7 中
        articles = soup.select('article.col-md-7')
        print(f"  找到 {len(articles)} 个资源条目")
        
        for article in articles[:20]:  # 每页最多取20个
            try:
                # 找到内部的链接元素
                link_elem = article.select_one('a.news-item')
                if not link_elem:
                    continue
                
                # 提取标题和详情页链接
                title = link_elem.get('title', '').strip()
                detail_url = link_elem.get('href', '')
                
                # 提取图片
                img_elem = article.select_one('img')
                img_url = img_elem.get('src', '') if img_elem else ''
                if img_url and not img_url.startswith('http'):
                    img_url = urljoin(self.base_url, img_url)
                
                # 提取发布日期
                date_elem = article.select_one('.transparent-grey span')
                date_str = date_elem.text.strip() if date_elem else ''
                
                resource = {
                    'name': title,
                    'url': detail_url,
                    'cover_image': img_url,
                    'date': date_str,
                    'category': category_name.strip('/'),
                    'source': 'mcpelife.com',
                    'crawled_at': datetime.now().isoformat(),
                    'download_urls': [],  # 将从详情页获取
                    'version': None,
                    'file_sizes': [],
                }
                
                resources.append(resource)
                
            except Exception as e:
                print(f"    ⚠️ 解析出错: {e}")
                continue
        
        return resources
    
    def parse_detail_page(self, html, base_resource):
        """解析详情页，提取版本信息和所有下载链接"""
        soup = BeautifulSoup(html, 'lxml')
        
        # 1. 从JSON-LD中提取版本信息
        script_tag = soup.find('script', type='application/ld+json')
        if script_tag:
            try:
                import json
                data = json.loads(script_tag.string)
                if isinstance(data, dict):
                    base_resource['version'] = data.get('softwareVersion')
                    # 也可以提取发布日期
                    if not base_resource.get('date') and data.get('datePublished'):
                        pub_date = data.get('datePublished')[:10]
                        base_resource['date'] = pub_date
            except:
                pass
        
        # 2. 提取所有下载链接
        download_wrap = soup.find('div', id='download')
        if download_wrap:
            download_items = download_wrap.find_all('div', class_='download-item')
            
            for item in download_items:
                # 提取架构/类型名称
                header = item.find('div', class_='item-header')
                arch_name = header.get_text(strip=True) if header else 'Unknown'
                
                # 提取下载链接
                link_elem = item.find('a', class_='green-bg')
                if link_elem and link_elem.get('href'):
                    download_url = urljoin(self.base_url, link_elem['href'])
                    
                    # 提取文件大小
                    size_elem = item.find('p', class_='transparent-grey')
                    file_size = size_elem.get_text(strip=True) if size_elem else 'Unknown'
                    
                    base_resource['download_urls'].append({
                        'arch': arch_name,
                        'url': download_url,
                        'size': file_size
                    })
        
        print(f"    ✅ 找到 {len(base_resource['download_urls'])} 个下载链接")
        return base_resource
    
    def load_existing_data(self):
        """加载已有数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_data(self, resources):
        """保存数据"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(resources, f, ensure_ascii=False, indent=2)
        print(f"✅ 数据已保存，共 {len(resources)} 个资源")
    
    def run(self):
        """运行爬虫"""
        print("🚀 开始爬取 mcpelife.com ...")
        all_new_resources = []
        
        # 1. 先爬取所有分类页面
        for category_url in self.category_urls:
            try:
                html = self.fetch_page(category_url)
                if not html:
                    continue
                
                resources = self.parse_category_page(html, category_url)
                print(f"  从 {category_url} 获取到 {len(resources)} 个资源")
                all_new_resources.extend(resources)
                
                # 礼貌性延迟
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                print(f"❌ 处理分类 {category_url} 失败: {e}")
                continue
        
        # 2. 加载已有数据用于去重
        existing = self.load_existing_data()
        existing_urls = {r.get('url') for r in existing}
        
        # 3. 筛选新资源并获取详情
        new_resources = []
        for resource in all_new_resources:
            if resource['url'] not in existing_urls:
                print(f"\n📥 获取新资源详情: {resource['name']}")
                html = self.fetch_page(resource['url'])
                if html:
                    resource = self.parse_detail_page(html, resource)
                    new_resources.append(resource)
                    time.sleep(random.uniform(2, 4))  # 详情页延迟长一点
        
        # 4. 合并数据（新资源放前面）
        if new_resources:
            merged = new_resources + existing
            self.save_data(merged[:200])  # 最多保存200个
            print(f"✨ 新增 {len(new_resources)} 个资源")
        else:
            print("📊 没有新资源")
            
        # 5. 运行更新脚本生成前端数据
        try:
            import subprocess
            subprocess.run(['python', 'scripts/update_site.py'], check=True)
        except:
            print("⚠️ 无法运行更新脚本")

if __name__ == '__main__':
    crawler = MCPECrawler()
    crawler.run()