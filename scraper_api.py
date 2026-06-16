#!/usr/bin/env python3
"""
FDA Drug Approval Reports Scraper - 使用 openFDA API
"""

import json
import os
from datetime import datetime, timedelta
import requests

# 配置
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# openFDA API 配置
OPENFDA_API = "https://api.fda.gov/drug/drugsfda.json"

def get_month_approvals(year, month):
    """获取指定年月的药物审批数据"""
    # 构建日期范围
    start_date = f"{year}{month:02d}01"
    
    # 计算月末日期
    if month == 12:
        end_date = f"{year}1231"
    else:
        next_month = month + 1
        next_month_date = datetime(year, next_month, 1) - timedelta(days=1)
        end_date = f"{year}{next_month:02d}{next_month_date.day:02d}"
    
    print(f"查询日期范围: {start_date} 到 {end_date}")
    
    # 构建查询参数
    # 查询原始批准（ORIG）和补充申请（SUPPL）
    # 注意：日期范围查询中的空格需要保持为空格，不能编码为 +
    search_query = f"submissions.submission_status_date:[{start_date} TO {end_date}]"
    
    all_results = []
    skip = 0
    max_results = 50  # 限制最多获取50条数据
    
    while True:
        try:
            print(f"请求 API (skip={skip})...")
            # 手动构建 URL 以避免 requests 自动编码 + 为 %2B
            url = f"{OPENFDA_API}?search={search_query}&limit=50&skip={skip}"
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"API 返回错误: {response.status_code}")
                break
            
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                break
            
            # 处理每条记录
            for item in results:
                submissions = item.get("submissions", [])
                
                for submission in submissions:
                    submission_date = submission.get("submission_status_date", "")
                    
                    # 检查是否在目标月份
                    if submission_date.startswith(f"{year}{month:02d}"):
                        # 提取药物信息
                        products = item.get("products", [])
                        openfda = item.get("openfda", {})
                        
                        # 获取药物名称
                        brand_name = openfda.get("brand_name", ["Unknown"])[0] if openfda.get("brand_name") else "Unknown"
                        generic_name = openfda.get("generic_name", ["Unknown"])[0] if openfda.get("generic_name") else "Unknown"
                        
                        # 获取申请号
                        application_number = item.get("application_number", "Unknown")
                        
                        # 格式化日期
                        formatted_date = f"{submission_date[:4]}-{submission_date[4:6]}-{submission_date[6:8]}"
                        
                        result = {
                            "drug_name": brand_name,
                            "generic_name": generic_name,
                            "application_number": application_number,
                            "submission_type": submission.get("submission_type", "Unknown"),
                            "submission_status": submission.get("submission_status", "Unknown"),
                            "approval_date": formatted_date,
                            "url": f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=DrugDetails.process&drugSeq={application_number}"
                        }
                        
                        all_results.append(result)
            
            # 检查是否还有更多数据
            total = data.get("meta", {}).get("results", {}).get("total", 0)
            skip += len(results)
            
            # 如果达到最大限制或没有更多数据，停止
            if len(all_results) >= max_results or skip >= total or len(results) < 50:
                break
                
        except Exception as e:
            print(f"请求失败: {e}")
            break
    
    return all_results

def save_results(results, year, month):
    """保存结果到文件"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 保存 JSON
    json_file = os.path.join(OUTPUT_DIR, f'fda_{year}_{month:02d}.json')
    data = {
        'year': year,
        'month': month,
        'scrape_time': datetime.now().isoformat(),
        'total': len(results),
        'results': results
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"JSON 已保存: {json_file}")
    
    # 保存 TSV
    tsv_file = os.path.join(OUTPUT_DIR, f'fda_{year}_{month:02d}.tsv')
    with open(tsv_file, 'w', encoding='utf-8') as f:
        f.write('药品名称\t通用名\t申请号\t提交类型\t状态\t审批日期\t链接\n')
        for r in results:
            f.write(f"{r['drug_name']}\t{r['generic_name']}\t{r['application_number']}\t{r['submission_type']}\t{r['submission_status']}\t{r['approval_date']}\t{r['url']}\n")
    
    print(f"TSV 已保存: {tsv_file}")
    
    return json_file, tsv_file

def main():
    print("=" * 60)
    print("FDA Drug Approval Reports 采集 (openFDA API)")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 测试查询 2025 年 6 月的数据
    test_year = 2025
    test_month = 6
    
    print(f"\n查询 {test_year} 年 {test_month} 月的药物审批数据")
    
    results = get_month_approvals(test_year, test_month)
    
    if results:
        json_file, tsv_file = save_results(results, test_year, test_month)
        print("\n" + "=" * 60)
        print(f"采集成功: {len(results)} 条数据")
        print(f"JSON 文件: {json_file}")
        print(f"TSV 文件: {tsv_file}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("采集失败: 未获取到数据")
        print("=" * 60)

if __name__ == '__main__':
    main()
