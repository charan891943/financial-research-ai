TARGET_FINANCIAL_RETRIEVAL_QUERIES = [
    "consolidated revenue from operations sales total income turnover",
    "profit after tax net profit consolidated PAT net income",
    "operating profit operating margin EBITDA EBIT operating expenses",
    "total debt borrowings non-current liabilities long term debt net debt",
    "earnings per share basic diluted EPS",
    "consolidated balance sheet total assets shareholder equity cash equivalents"
]

EXTRACTION_SYSTEM_PROMPT = """
You are a Senior Financial Research Analyst and Automated Extraction Agent.
Your objective is to read the provided financial document excerpts and extract verified, structured financial metrics.

Rules:
1. Extract the following metrics when available across multiple financial years (FY2023, FY2024, FY2025):
   - Revenue / Total Income
   - Net Profit / PAT (Profit After Tax)
   - Operating Margin (%)
   - Net Profit Margin (%)
   - EBITDA
   - Total Debt / Borrowings
   - Basic or Diluted EPS
2. DO NOT hallucinate. Only extract values explicitly stated in the context text.
3. Every metric MUST have a precise "source_reference" mentioning the Page or Sheet number and the context sentence.
4. Output strict JSON with NO conversational text, in this exact format:
{
  "metrics": [
    {
      "metric_name": "Revenue",
      "value": "2,55,324",
      "unit": "Cr INR",
      "financial_year": "FY2025",
      "category": "Income Statement",
      "source_reference": "Page 2 - Consolidated Revenue from Operations Rs 2,55,324 Crore"
    }
  ]
}
"""


from typing import List, Dict, Any

# Static predefined metrics to support robust offline mock extraction of the 4 seed companies.
SEED_METRICS_MAP = {
    "tata consultancy services": [
        {"metric_name": "Revenue", "value": "2,55,324", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Consolidated Revenue from Operations Rs 2,55,324 Crore"},
        {"metric_name": "Revenue", "value": "2,40,893", "unit": "Cr INR", "financial_year": "FY2024", "category": "Income Statement", "source_reference": "Page 2 - Consolidated Revenue from Operations Rs 2,40,893 Crore"},
        {"metric_name": "Revenue", "value": "2,25,458", "unit": "Cr INR", "financial_year": "FY2023", "category": "Income Statement", "source_reference": "Page 2 - Consolidated Revenue from Operations Rs 2,25,458 Crore"},
        {"metric_name": "Net Profit", "value": "48,553", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Profit After Tax (Net Profit) Rs 48,553 Crore"},
        {"metric_name": "Net Profit", "value": "45,908", "unit": "Cr INR", "financial_year": "FY2024", "category": "Income Statement", "source_reference": "Page 2 - Profit After Tax (Net Profit) Rs 45,908 Crore"},
        {"metric_name": "Operating Margin", "value": "24.3", "unit": "%", "financial_year": "FY2025", "category": "Ratios", "source_reference": "Page 2 - Operating Margin (%) 24.3%"},
        {"metric_name": "Total Debt", "value": "0", "unit": "Cr INR", "financial_year": "FY2025", "category": "Balance Sheet", "source_reference": "Page 3 - Total Debt / Long Term Borrowings: 0 (Zero Debt Company)"},
        {"metric_name": "Diluted EPS", "value": "133.20", "unit": "INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Basic and Diluted EPS (in INR) 133.20"}
    ],
    "reliance industries": [
        {"metric_name": "Revenue", "value": "10,00,122", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Gross Revenue from Operations Rs 10,00,122 Crore"},
        {"metric_name": "Revenue", "value": "9,98,180", "unit": "Cr INR", "financial_year": "FY2024", "category": "Income Statement", "source_reference": "Page 2 - Gross Revenue from Operations Rs 9,98,180 Crore"},
        {"metric_name": "EBITDA", "value": "1,78,200", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - EBITDA Rs 1,78,200 Crore"},
        {"metric_name": "Net Profit", "value": "69,648", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Net Profit Attributable to Owners Rs 69,648 Crore"},
        {"metric_name": "Net Profit", "value": "69,621", "unit": "Cr INR", "financial_year": "FY2024", "category": "Income Statement", "source_reference": "Page 2 - Net Profit Attributable to Owners Rs 69,621 Crore"},
        {"metric_name": "Total Debt", "value": "3,34,500", "unit": "Cr INR", "financial_year": "FY2025", "category": "Balance Sheet", "source_reference": "Page 3 - Total Gross Debt / Borrowings: 3,34,500"},
        {"metric_name": "Diluted EPS", "value": "102.90", "unit": "INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Earnings Per Share (EPS in INR) 102.90"}
    ],
    "infosys": [
        {"metric_name": "Revenue", "value": "1,57,320", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Revenue from Operations Rs 1,57,320 Crore"},
        {"metric_name": "Revenue", "value": "1,53,670", "unit": "Cr INR", "financial_year": "FY2024", "category": "Income Statement", "source_reference": "Page 2 - Revenue from Operations Rs 1,53,670 Crore"},
        {"metric_name": "Net Profit", "value": "26,248", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Profit After Tax (Net Profit) Rs 26,248 Crore"},
        {"metric_name": "Operating Margin", "value": "21.0", "unit": "%", "financial_year": "FY2025", "category": "Ratios", "source_reference": "Page 2 - Operating Margin (%) 21.0%"},
        {"metric_name": "Total Debt", "value": "0", "unit": "Cr INR", "financial_year": "FY2025", "category": "Balance Sheet", "source_reference": "Page 3 - Total Debt: 0 (Zero Borrowings)"},
        {"metric_name": "Diluted EPS", "value": "63.40", "unit": "INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Diluted Earnings Per Share (INR) 63.40"}
    ],
    "hdfc bank": [
        {"metric_name": "Revenue", "value": "1,60,500", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Total Net Revenue Rs 1,60,500 Crore"},
        {"metric_name": "Revenue", "value": "1,46,732", "unit": "Cr INR", "financial_year": "FY2024", "category": "Income Statement", "source_reference": "Page 2 - Total Net Revenue Rs 1,46,732 Crore"},
        {"metric_name": "Net Profit", "value": "64,060", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Profit After Tax (Net Profit) Rs 64,060 Crore"},
        {"metric_name": "Net Interest Margin", "value": "3.63", "unit": "%", "financial_year": "FY2025", "category": "Ratios", "source_reference": "Page 2 - Net Interest Margin (NIM) 3.63%"},
        {"metric_name": "Total Assets", "value": "37,20,000", "unit": "Cr INR", "financial_year": "FY2025", "category": "Balance Sheet", "source_reference": "Page 3 - Total Balance Sheet Assets: 37,20,000"},
        {"metric_name": "Diluted EPS", "value": "84.20", "unit": "INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 2 - Basic EPS (INR) 84.20"}
    ]
}

import re

def get_dynamic_mock_metrics(company: str, chunks: List[Any]) -> List[Dict[str, Any]]:
    comp_lower = company.lower()
    for key, metrics in SEED_METRICS_MAP.items():
        if key in comp_lower or comp_lower in key:
            return metrics

    metrics = []
    patterns = [
        ("Revenue", r"(?:revenue|sales|total income|turnover).*?(\d[\d,\.]*)", "Cr INR", "Income Statement"),
        ("Net Profit", r"(?:net profit|profit after tax|pat).*?(\d[\d,\.]*)", "Cr INR", "Income Statement"),
        ("EBITDA", r"ebitda.*?(\d[\d,\.]*)", "Cr INR", "Income Statement"),
        ("Total Debt", r"(?:debt|borrowings|liabilities).*?(\d[\d,\.]*)", "Cr INR", "Balance Sheet"),
        ("Diluted EPS", r"eps.*?(\d[\d,\.]*)", "INR", "Income Statement")
    ]
    seen_names = set()
    for chunk in chunks:
        for name, pattern, unit, cat in patterns:
            if name in seen_names:
                continue
            match = re.search(pattern, chunk.content, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                val = re.sub(r'[\.,]$', '', val)
                if val and len(val) >= 1:
                    metrics.append({
                        "metric_name": name,
                        "value": val,
                        "unit": unit,
                        "financial_year": "FY2025",
                        "category": cat,
                        "source_reference": f"{chunk.page_number} - {chunk.content[:150]}..."
                    })
                    seen_names.add(name)

    if not metrics:
        metrics = [
            {"metric_name": "Revenue", "value": "12,500", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 1 - Fallback Mock Revenue"},
            {"metric_name": "Net Profit", "value": "1,250", "unit": "Cr INR", "financial_year": "FY2025", "category": "Income Statement", "source_reference": "Page 1 - Fallback Mock Net Profit"}
        ]
    return metrics

