#!/usr/bin/env python3
"""
FDA Drug Approval Reports 采集脚本
适用于 GitHub Actions 环境（Playwright + Chromium）
"""

import json
import os
import re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

# 配置
OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 目标 URL
FDA_BASE_URL = "https://www.accessdata.fda.gov/scripts/cder/daf/"
APPROVAL_REPORTS_URL = "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process"


def parse_date(date_str):
    """解析日期字符串，返回 YYYY-MM-DD 格式"""
    if not date_str:
        return None
    
    # 尝试多种格式
    patterns = [
        (r"(\d{1,2})/(\d{1,2})/(\d{4})", "%m/%d/%Y"),  # 12/31/2024
        (r"(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),      # 2024-12-31
        (r"(\d{1,2})-(\d{1,2})-(\d{4})", "%m-%d-%Y"),  # 12-31-2024
    ]
    
    for pattern, fmt in patterns:
        match = re.search(pattern, date_str.strip())
        if match:
            try:
                date_obj = datetime.strptime(date_str.strip(), fmt)
                return date_obj.strftime("%Y-%m-%d")
            except:
                continue
    
    return date_str.strip()


def scrape_fda():
    """采集 FDA 药物审批数据"""
    results = []
    errors = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            print(f"[INFO] 访问 FDA 主页: {FDA_BASE_URL}")
            page.goto(FDA_BASE_URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # 点击 "Drug Approval Reports by Month"
            print("[INFO] 点击 Drug Approval Reports by Month...")
            approval_link = page.locator("a:has-text('Drug Approval Reports by Month')")
            approval_link.click()
            page.wait_for_load_state("networkidle")
            
            # 选择报告类型：New Drug Approvals (单选按钮 value="2")
            print("[INFO] 选择报告类型...")
            page.locator("input[name='rptname'][value='2']").check()
            
            # 选择年月（当前年月）
            now = datetime.now()
            year = now.year
            month = now.month
            
            print(f"[INFO] 选择年月: {year}年{month}月")
            page.locator("select[name='reportSelectYear']").select_option(str(year))
            page.locator("select[name='reportSelectMonth']").select_option(str(month))
            
            # 提交表单
            print("[INFO] 提交表单...")
            page.locator("input[type='submit'][value='Submit']").click()
            page.wait_for_load_state("networkidle")
            
            # 等待结果表格
            print("[INFO] 等待结果...")
            page.wait_for_selector("table", timeout=30000)
            
            # 提取表格数据
            print("[INFO] 提取数据...")
            rows = page.locator("table tr").all()
            
            for row in rows[1:]:  # 跳过表头
                cols = row.locator("td").all()
                if len(cols) >= 3:
                    try:
                        drug_name = cols[0].inner_text().strip()
                        active_ingredient = cols[1].inner_text().strip()
                        approval_date = cols[2].inner_text().strip()
                        
                        if drug_name and approval_date:
                            results.append({
                                "drug_name": drug_name,
                                "active_ingredient": active_ingredient,
                                "approval_date": parse_date(approval_date),
                                "url": page.url
                            })
                    except Exception as e:
                        print(f"[WARN] 解析行失败: {e}")
                        continue
            
            print(f"[SUCCESS] 采集到 {len(results)} 条数据")
            
        except Exception as e:
            error_msg = f"采集失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            errors.append({
                "url": FDA_BASE_URL,
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            })
        
        finally:
            browser.close()
    
    return results, errors


def save_results(results, errors):
    """保存结果到 JSON 文件"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    output = {
        "date": today,
        "crawl_time": datetime.now().isoformat(),
        "total": len(results),
        "results": results,
        "errors": errors
    }
    
    # 保存 JSON
    json_path = os.path.join(OUTPUT_DIR, f"fda_{today}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"[INFO] 数据已保存: {json_path}")
    
    # 保存 TSV（方便查看）
    tsv_path = os.path.join(OUTPUT_DIR, f"fda_{today}.tsv")
    with open(tsv_path, "w", encoding="utf-8") as f:
        f.write("药品名称\t活性成分\t审批日期\t链接\n")
        for r in results:
            f.write(f"{r['drug_name']}\t{r['active_ingredient']}\t{r['approval_date']}\t{r['url']}\n")
    
    print(f"[INFO] TSV 已保存: {tsv_path}")
    
    return json_path, tsv_path


def main():
    print("=" * 60)
    print("FDA Drug Approval Reports 采集")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results, errors = scrape_fda()
    json_path, tsv_path = save_results(results, errors)
    
    print("=" * 60)
    print(f"采集完成: {len(results)} 条数据, {len(errors)} 个错误")
    print("=" * 60)
    
    # 输出结果供 GitHub Actions 使用
    if results:
        print("\n采集结果:")
        for r in results[:5]:  # 只显示前5条
            print(f"  - {r['drug_name']} ({r['approval_date']})")
        if len(results) > 5:
            print(f"  ... 还有 {len(results) - 5} 条")


if __name__ == "__main__":
    main()
