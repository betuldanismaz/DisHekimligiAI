from app.rules.clinical_rules import get_rules_for_category

class RuleService:
    """
    Vaka kategorisine göre doğru tıbbi kuralları getiren servis.
    """
    
    def get_active_rules(self, scenario_category: str):
        # Kategori ismini büyük harfe çevirip eşleşme ara
        category_key = scenario_category.upper().replace(" ", "_")
        
        rules = get_rules_for_category(category_key)
        
        if not rules:
            # Eğer kural bulunamazsa varsayılan güvenli kurallar döndür
            return {
                "critical_safety_rules": ["Do no harm.", "Take detailed patient history."],
                "note": "No specific rules found for this category."
            }
        
        return rules

# Singleton instance
rule_service = RuleService()