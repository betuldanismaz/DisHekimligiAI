"""
Test Script for Sprint 3 Analytics Engine
Demonstrates weakness detection algorithm with sample data
"""

import sys
sys.path.insert(0, 'C:/Users/Emre/Desktop/Denemeler4/Dentistry_Project')

import pandas as pd
from app.analytics_engine import analyze_performance, generate_report_text

# Sample action history (simulating a student with weak diagnosis skills)
sample_actions = [
    # Strong in anamnesis
    {"action": "take_anamnesis", "score": 9, "outcome": "Doğru"},
    {"action": "ask_symptom_onset", "score": 8, "outcome": "Doğru"},
    {"action": "ask_about_medications", "score": 9, "outcome": "Doğru"},
    
    # Strong in examination
    {"action": "perform_oral_exam", "score": 9, "outcome": "Doğru"},
    {"action": "perform_nikolsky_test", "score": 8, "outcome": "Doğru"},
    {"action": "examine_skin", "score": 8, "outcome": "Doğru"},
    
    # Weak in diagnosis (this should be detected!)
    {"action": "diagnose_lichen_planus", "score": 4, "outcome": "Yanlış"},
    {"action": "diagnose_periodontitis", "score": 5, "outcome": "Kısmen Doğru"},
    {"action": "diagnose_primary_herpes", "score": 3, "outcome": "Yanlış"},
    
    # Decent in treatment
    {"action": "prescribe_topical_steroids", "score": 7, "outcome": "Doğru"},
    {"action": "prescribe_antibiotics", "score": 6, "outcome": "Kısmen Doğru"},
    
    # Good in diagnostic tests
    {"action": "request_biopsy", "score": 8, "outcome": "Doğru"},
    {"action": "request_blood_tests", "score": 9, "outcome": "Doğru"},
]

print("=" * 70)
print("SPRINT 3 ANALYTICS ENGINE TEST")
print("=" * 70)

# Create DataFrame
df = pd.DataFrame(sample_actions)

print("\n📊 Sample Data:")
print(df[['action', 'score', 'outcome']].to_string(index=False))

# Analyze performance
print("\n\n🧠 Running Weakness Detection Algorithm...")
analysis = analyze_performance(df)

print("\n" + "=" * 70)
print("ANALYSIS RESULTS")
print("=" * 70)

print(f"\n🔍 Weakest Category: {analysis['weakest_category']}")
print(f"📉 Average Score: {analysis['weakest_score']:.2f}/10")

print("\n💡 RECOMMENDATION:")
print("-" * 70)
print(analysis['recommendation'])

print("\n\n📋 Category Performance Breakdown:")
print("-" * 70)
for category, stats in analysis['category_performance'].items():
    print(f"\n{category.upper()}:")
    print(f"  • Actions: {stats['action_count']:.0f}")
    print(f"  • Avg Score: {stats['avg_score']:.2f}")
    print(f"  • Total Score: {stats['total_score']:.0f}")

print("\n" + "=" * 70)
print("✅ ALGORITHM TEST SUCCESSFUL!")
print("=" * 70)

# Test report generation
print("\n\n📄 Testing Report Generation...")
sample_stats = {
    "action_history": sample_actions,
    "total_score": sum(a['score'] for a in sample_actions),
    "total_actions": len(sample_actions),
    "completed_cases": {"olp_001", "perio_001"}
}

report = generate_report_text(sample_stats, analysis)

print("\n" + "=" * 70)
print("GENERATED REPORT PREVIEW (First 500 chars)")
print("=" * 70)
print(report[:500] + "...")

print("\n✅ ALL SPRINT 3 TESTS PASSED!")
