#!/usr/bin/env python3
"""
FDA Drug Approval Reports Scraper
用于 GitHub Actions 环境
"""

import json
import os
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# 配置
FDA_URL = "https://www.accessdata.fda.gov/scripts/cder/daf/"
OUTPUT_DIR = "data"
MAX_RETRIES = 3
TIMEOUT = 120000  # 120秒超时

def ensure_output_dir():
    """确保输出目录存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_date(date_str):
    """解析日期字符串"""
    if not date_str:
        return None
    
    # 尝试多种日期格式
    patterns = [
        r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
        r'(\d{2})/(\d{2})/(\d{4})',  # MM/DD/YYYY
        r'(\d{1,2})/(\d{1,2})/(\d{4})',  # M/D/YYYY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_str)
        if match:
            return match.group(0)
    
    return date_str

def scrape_fda():
    """采集 FDA 数据"""
    results = []
    errors = []
    
    with sync_playwright() as p:
        browser = None
        for attempt in range(MAX_RETRIES):
            try:
                print(f"[尝试 {attempt + 1}/{MAX_RETRIES}] 启动浏览器...")
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox']
                )
                
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = context.new_page()
                page.set_default_timeout(TIMEOUT)
                
                print(f"访问 {FDA_URL}")
                page.goto(FDA_URL, wait_until='networkidle', timeout=TIMEOUT)
                
                print("页面加载完成，等待内容...")
                page.wait_for_timeout(5000)  # 等待5秒
                
                # 检查是否有 Drug Approval Reports 链接
                print("查找 Drug Approval Reports 链接...")
                approval_link = page.locator('a:has-text("Drug Approval Reports")').first
                if approval_link.is_visible(timeout=10000):
                    print("找到链接，点击进入...")
                    approval_link.click()
                    page.wait_for_load_state('networkidle', timeout=TIMEOUT)
                    
                    # 选择报告类型
                    print("选择报告类型...")
                    report_type_select = page.locator('select[name="reportType"]').first
                    if report_type_select.is_visible(timeout=10000):
                        report_type_select.select_option(label='New Drug Approvals')
                        
                        # 选择年月
                        print("选择年月...")
                        year_select = page.locator('select[name="year"]').first
                        month_select = page.locator('select[name="month"]').first
                        
                        if year_select.is_visible(timeout=10000):
                            current_year = datetime.now().year
                            year_select.select_option(value=str(current_year))
                            
                        if month_select.is_visible(timeout=10000):
                            current_month = datetime.now().month
                            month_select.select_option(value=str(current_month))
                            
                            # 提交查询
                            print("提交查询...")
                            submit_btn = page.locator('input[type="submit"], button[type="submit"]').first
                            if submit_btn.is_visible(timeout=10000):
                                submit_btn.click()
                                page.wait_for_load_state('networkidle', timeout=TIMEOUT)
                                
                                # 提取表格数据
                                print("提取数据...")
                                page.wait_for_timeout(3000)
                                
                                # 查找表格
                                tables = page.locator('table').all()
                                if tables:
                                    print(f"找到 {len(tables)} 个表格")
                                    
                                    # 遍历所有表格查找数据
                                    for table_idx, table in enumerate(tables):
                                        rows = table.locator('tr').all()
                                        print(f"表格 {table_idx}: {len(rows)} 行")
                                        
                                        for row_idx, row in enumerate(rows):
                                            cells = row.locator('td, th').all()
                                            if len(cells) >= 3:  # 至少3列
                                                try:
                                                    drug_name = cells[0].inner_text().strip()
                                                    active_ingredient = cells[1].inner_text().strip()
                                                    approval_date = cells[2].inner_text().strip()
                                                    
                                                    # 跳过表头
                                                    if drug_name.lower() in ['drug name', 'trade name', 'generic name', '']:
                                                        continue
                                                    
                                                    # 解析日期
                                                    parsed_date = parse_date(approval_date)
                                                    
                                                    results.append({
                                                        'drug_name': drug_name,
                                                        'active_ingredient': active_ingredient,
                                                        'approval_date': parsed_date,
                                                        'url': page.url
                                                    })
                                                except Exception as e:
                                                    print(f"解析行 {row_idx} 失败: {e}")
                                                    continue
                                
                                print(f"采集到 {len(results)} 条数据")
                                break
                            else:
                                errors.append(f"未找到提交按钮")
                        else:
                            errors.append(f"未找到年月选择器")
                    else:
                        errors.append(f"未找到报告类型选择器")
                else:
                    errors.append(f"未找到 Drug Approval Reports 链接")
                
                # 如果成功采集到数据，跳出重试循环
                if results:
                    break
                    
            except Exception as e:
                error_msg = f"尝试 {attempt + 1} 失败: {str(e)}"
                print(f"[错误] {error_msg}")
                errors.append(error_msg)
                
                if attempt < MAX_RETRIES - 1:
                    print(f"等待 5 秒后重试...")
                    page.wait_for_timeout(5000)
            
            finally:
                if browser:
                    try:
                        browser.close()
                    except:
                        pass
    
    return results, errors

def save_results(results, errors):
    """保存结果到文件"""
    ensure_output_dir()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 保存 JSON
    json_file = os.path.join(OUTPUT_DIR, f'fda_{today}.json')
    data = {
        'date': today,
        'scrape_time': datetime.now().isoformat(),
        'total': len(results),
        'results': results,
        'errors': errors
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"JSON 已保存: {json_file}")
    
    # 保存 TSV
    tsv_file = os.path.join(OUTPUT_DIR, f'fda_{today}.tsv')
    with open(tsv_file, 'w', encoding='utf-8') as f:
        f.write('药品名称\t活性成分\t审批日期\t链接\n')
        for r in results:
            f.write(f"{r['drug_name']}\t{r['active_ingredient']}\t{r['approval_date']}\t{r['url']}\n")
    
    print(f"TSV 已保存: {tsv_file}")
    
    return json_file, tsv_file

def main():
    print("=" * 60)
    print("FDA Drug Approval Reports 采集")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results, errors = scrape_fda()
    
    if results:
        json_file, tsv_file = save_results(results, errors)
        print("\n" + "=" * 60)
        print(f"采集成功: {len(results)} 条数据")
        print(f"文件: {json_file}")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("采集失败: 未获取到数据")
        print("错误信息:")
        for err in errors:
            print(f"  - {err}")
        print("=" * 60)
        
        # 即使失败也保存错误信息
        save_results([], errors)

if __name__ == '__main__':
    main()
