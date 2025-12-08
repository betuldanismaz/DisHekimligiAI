"""
CLINICAL RULES DATABASE
-----------------------
This file contains the single source of truth for medical rules used by
MedGemma (AI Validator) and Gemini (AI Agent).

Structure: Python Dictionary (JSON compatible)
"""

# Constants (to prevent typos)
CAT_INFECTIOUS = "INFECTIOUS"
CAT_NEOPLASTIC = "NEOPLASTIC"
CAT_IMMUNOLOGIC = "IMMUNOLOGIC"
CAT_TRAUMATIC = "TRAUMATIC"
CAT_DEVELOPMENTAL = "DEVELOPMENTAL"
CAT_SYSTEMIC = "SYSTEMIC"
CAT_REACTIVE = "REACTIVE"
CAT_RARE = "RARE"

# Main Rules Database
CLINICAL_RULES_DB = {
    CAT_INFECTIOUS: {
        "critical_safety_rules": [
            "NEVER prescribe Penicillin-group antibiotics (Amoxicillin, Augmentin, Penicillin V) to patients with documented Penicillin allergy.",
            "Check for drug allergies before prescribing antibiotics.",
            "Confirm pregnancy status before prescribing Tetracycline or Metronidazole.",
            "Verify renal function before prescribing high-dose antibiotics in elderly patients."
        ],
        "recommended_antibiotics": {
            "first_line": ["Amoxicillin 500mg TID", "Amoxicillin-Clavulanate 875/125mg BID"],
            "penicillin_allergy": ["Clindamycin 300mg QID", "Azithromycin 500mg OD", "Clarithromycin 500mg BID"],
            "pregnancy_safe": ["Amoxicillin", "Cephalexin"],
            "pregnancy_contraindicated": ["Tetracycline", "Metronidazole (1st trimester)"]
        },
        "required_history": [
            "Drug allergy history (especially Penicillin)",
            "Pregnancy status for female patients of childbearing age",
            "Renal/hepatic function in elderly or compromised patients"
        ],
        "diagnostic_requirements": [
            "Clinical examination for signs of spreading infection",
            "Consider radiograph if suspected osteomyelitis"
        ]
    },
    
    CAT_IMMUNOLOGIC: {
        "critical_safety_rules": [
            "Identify Wickham striae pattern in Oral Lichen Planus cases.",
            "Rule out pemphigus/pemphigoid before starting topical corticosteroids.",
            "Check for systemic autoimmune disease associations.",
            "Monitor for malignant transformation in erosive lichen planus."
        ],
        "diagnostic_criteria": {
            "oral_lichen_planus": [
                "Bilateral reticular white lines (Wickham striae)",
                "Symmetric distribution on buccal mucosa",
                "Erosive or atrophic variants on tongue/gingiva"
            ]
        },
        "recommended_treatment": {
            "topical_corticosteroids": ["Triamcinolone acetonide 0.1%", "Betamethasone 0.05%"],
            "systemic_therapy": ["Only for severe erosive cases after specialist consultation"]
        },
        "required_history": [
            "Medication history (especially ACE inhibitors, NSAIDs)",
            "Autoimmune disease history",
            "Hepatitis C screening in chronic cases"
        ]
    },
    
    CAT_NEOPLASTIC: {
        "critical_safety_rules": [
            "ANY ulcer not healing within 2 weeks must be biopsied.",
            "Refer immediately if suspicion of malignancy (indurated borders, fixation to underlying tissue).",
            "Document lesion size, location, and appearance with photography.",
            "Check for cervical lymphadenopathy in all suspected malignant lesions."
        ],
        "red_flags": [
            "Non-healing ulcer >2 weeks",
            "Indurated or rolled borders",
            "Fixation to underlying structures",
            "Cervical lymphadenopathy",
            "History of tobacco/alcohol use"
        ],
        "required_actions": [
            "Incisional or excisional biopsy",
            "Referral to oral surgeon or oncologist",
            "Complete medical and social history (tobacco, alcohol, HPV risk)"
        ]
    },
    
    CAT_TRAUMATIC: {
        "critical_safety_rules": [
            "Assess airway if facial trauma involves mandible fracture.",
            "Check for cervical spine injury in high-impact trauma.",
            "Rule out tooth avulsion/subluxation in all oral trauma cases.",
            "Tetanus prophylaxis status must be verified."
        ],
        "immediate_actions": [
            "Control bleeding",
            "Assess for fractures (clinical + radiographic)",
            "Check for foreign body retention",
            "Verify tetanus immunization status"
        ],
        "required_history": [
            "Mechanism of injury",
            "Time of injury",
            "Loss of consciousness or neurological symptoms",
            "Tetanus vaccination history"
        ]
    },
    
    CAT_SYSTEMIC: {
        "critical_safety_rules": [
            "Check HbA1c levels in diabetic patients before surgery.",
            "Verify INR in patients on anticoagulants before invasive procedures.",
            "Adjust antibiotic regimen for patients with renal/hepatic impairment.",
            "Request endocarditis prophylaxis for high-risk cardiac patients."
        ],
        "diabetes_management": {
            "uncontrolled_diabetes": "Defer elective surgery if HbA1c >8.5%",
            "infection_risk": "High risk of post-operative infection",
            "antibiotic_adjustment": "Consider longer course or prophylactic regimen"
        },
        "anticoagulation_management": {
            "warfarin": "Check INR <3.5 for minor surgery, consider bridging for major procedures",
            "DOACs": "Hold 24-48h before surgery depending on renal function"
        }
    }
}

def get_rules_for_category(category_key: str) -> dict:
    """
    Retrieves clinical rules for a specific pathology category.
    
    Args:
        category_key: Category name (e.g., 'INFECTIOUS', 'IMMUNOLOGIC')
        
    Returns:
        Dictionary of clinical rules, or empty dict if category not found
    """
    return CLINICAL_RULES_DB.get(category_key.upper(), {})

def get_all_categories() -> list:
    """Returns a list of all available rule categories."""
    return list(CLINICAL_RULES_DB.keys())

def validate_category(category_key: str) -> bool:
    """Checks if a category exists in the rules database."""
    return category_key.upper() in CLINICAL_RULES_DB

# For backward compatibility and easy access
def get_infectious_rules():
    return get_rules_for_category(CAT_INFECTIOUS)

def get_immunologic_rules():
    return get_rules_for_category(CAT_IMMUNOLOGIC)

def get_neoplastic_rules():
    return get_rules_for_category(CAT_NEOPLASTIC)