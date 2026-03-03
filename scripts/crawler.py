#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MCPE资源爬虫
自动抓取手机版我的世界资源
"""

import requests
import json
import os
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from retry import retry

class MCPECrawler:
    """MCPE资源爬虫类"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.data_dir = 'data'
        self.data_file = os.path.join(self.data_dir, 'resources.json')
        
        # 需要根据实际可访问的网站修改
        self.source_urls = [
            'https://mcpelife.com'
            # 请替换为实际可用的网站
        ]
        
        # 创建数据目录
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_headers(self):
        """生成随机请求头"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    @retry(tries=3, delay=2, backoff=2)
    def fetch_page(self, url):
        """获取页面内容（带重试机制）"""
        try:
            response = requests.get(
                url, 
                headers=self.get_headers(),
                timeout=15,
                allow_redirects=True
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"❌ 请求失败 {url}: {e}")
            raise
    
    def parse_mcpedl(self, html):
        """解析MCPEDL网站（示例选择器）"""
        soup = BeautifulSoup(html, 'lxml')
        resources = []
        
        # TODO: 根据实际网页结构调整CSS选择器
        items = soup.select('.post-item')  # 示例选择器
        
        for item in items[:10]:  # 每次抓取前10个
            try:
                title_elem = item.select_one('.entry-title a')
                img_elem = item.select_one('.post-thumbnail img')
                download_elem = item.select_one('.download-link a')
                desc_elem = item.select_one('.entry-content p')
                
                resource = {
                    'name': title_elem.text.strip() if title_elem else '未知',
                    'url': title_elem.get('href') if title_elem else '',
                    'cover_image': img_elem.get('src') if img_elem else '',
                    'download_url': download_elem.get('href') if download_elem else '',
                    'description': desc_elem.text.strip()[:200] if desc_elem else '暂无描述',
                    'source': 'mcpedl',
                    'crawled_at': datetime.now().isoformat(),
                }
                
                # 只保留有下载链接的资源
                if resource['download_url']:
                    resources.append(resource)
                    
            except Exception as e:
                print(f"⚠️ 解析单个资源失败: {e}")
                continue
        
        return resources
    
    def load_existing_data(self):
        """加载已有的数据"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def merge_resources(self, new_resources, existing_resources):
        """合并新旧资源，去重"""
        # 使用URL作为唯一标识
        existing_urls = {r.get('url') for r in existing_resources}
        
        for resource in new_resources:
            if resource.get('url') and resource['url'] not in existing_urls:
                existing_resources.insert(0, resource)  # 新资源放前面
        
        # 限制总数量，防止过大
        return existing_resources[:100]
    
    def save_data(self, resources):
        """保存数据到JSON文件"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(resources, f, ensure_ascii=False, indent=2)
        print(f"✅ 数据已保存到 {self.data_file}，共 {len(resources)} 个资源")
    
    def run(self):
        """运行爬虫"""
        print("🚀 开始爬取MCPE资源...")
        all_new_resources = []
        
        for url in self.source_urls:
            try:
                print(f"🌐 正在爬取: {url}")
                html = self.fetch_page(url)
                
                # 根据URL选择不同的解析器
                if 'mcpedl' in url:
                    resources = self.parse_mcpedl(html)
                else:
                    # 可以添加其他网站的解析器
                    continue
                
                print(f"   ✅ 获取到 {len(resources)} 个资源")
                all_new_resources.extend(resources)
                
                # 礼貌性延迟，避免请求过快
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"❌ 爬取 {url} 失败: {e}")
                continue
        
        if all_new_resources:
            existing = self.load_existing_data()
            merged = self.merge_resources(all_new_resources, existing)
            self.save_data(merged)
            print(f"✨ 爬取完成！新增 {len(all_new_resources)} 个资源")
        else:
            print("⚠️ 没有获取到新资源")

if __name__ == '__main__':
    crawler = MCPECrawler()
    crawler.run()