#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网站数据更新脚本
对爬取的数据进行二次处理，生成适合前端展示的格式
"""

import json
import os
from datetime import datetime

def process_resources():
    """处理原始数据，生成前端友好格式"""
    data_file = 'data/resources.json'
    
    if not os.path.exists(data_file):
        print("❌ 数据文件不存在")
        return
    
    with open(data_file, 'r', encoding='utf-8') as f:
        resources = json.load(f)
    
    # 为前端添加额外字段
    for r in resources:
        # 格式化日期
        if 'crawled_at' in r:
            try:
                dt = datetime.fromisoformat(r['crawled_at'])
                r['date_formatted'] = dt.strftime('%Y-%m-%d')
            except:
                r['date_formatted'] = '未知'
        
        # 确保所有必要字段都存在
        r.setdefault('version', '未知')
        r.setdefault('category', '其他')
    
    # 按分类统计
    categories = {}
    for r in resources:
        cat = r.get('category', '其他')
        categories[cat] = categories.get(cat, 0) + 1
    
    # 保存处理后的数据和统计信息
    output = {
        'last_update': datetime.now().isoformat(),
        'total_count': len(resources),
        'categories': categories,
        'resources': resources
    }
    
    with open('data/site_data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 网站数据处理完成，共 {len(resources)} 个资源，{len(categories)} 个分类")

if __name__ == '__main__':
    process_resources()