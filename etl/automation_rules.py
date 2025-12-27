"""
Règles d'Automatisation Phase 3
Version: 1.0
Auteur: Projet CRM Ruhlmann

Rôle: Définir et gérer les règles d'automatisation
  - Scoring client dynamique
  - Follow-up sequences
  - Lead nurturing
  - Multi-channel automation
  - Decision logic
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from etl.config import logger


class ActionType(Enum):
    """
    Types d'actions d'automatisation
    """
    SEND_EMAIL = "send_email"
    UPDATE_SCORE = "update_score"
    ADD_TAG = "add_tag"
    CREATE_TASK = "create_task"
    SCHEDULE_CALL = "schedule_call"
    PAUSE_CAMPAIGN = "pause_campaign"
    SEND_SMS = "send_sms"
    TRIGGER_WEBHOOK = "trigger_webhook"


class TriggerType(Enum):
    """
    Types de déclencheurs
    """
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_BOUNCE = "email_bounce"
    PAGE_VISIT = "page_visit"
    PURCHASE = "purchase"
    FORM_SUBMIT = "form_submit"
    TIME_BASED = "time_based"
    UNSUBSCRIBE = "unsubscribe"
    LEAD_SCORE_HIGH = "lead_score_high"


@dataclass
class AutomationAction:
    """
    Définition d'une action d'automatisation
    """
    action_type: ActionType
    config: Dict
    delay_minutes: int = 0  # Attendre X minutes avant d'exécuter
    
    def to_dict(self) -> Dict:
        return {
            'action_type': self.action_type.value,
            'config': self.config,
            'delay_minutes': self.delay_minutes
        }


@dataclass
class AutomationRule:
    """
    Définition d'une règle d'automatisation
    """
    rule_id: str
    trigger: TriggerType
    conditions: Dict = field(default_factory=dict)
    actions: List[AutomationAction] = field(default_factory=list)
    enabled: bool = True
    priority: int = 50  # 1-100, plus élevé = priorité plus haute
    description: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'rule_id': self.rule_id,
            'trigger': self.trigger.value,
            'conditions': self.conditions,
            'actions': [a.to_dict() for a in self.actions],
            'enabled': self.enabled,
            'priority': self.priority,
            'description': self.description
        }


class AutomationRuleEngine:
    """
    Moteur de règles d'automatisation
    """
    
    def __init__(self):
        """
        Initialise le moteur de règles
        """
        self.rules: List[AutomationRule] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """
        Charge les règles d'automatisation par défaut
        """
        # Règle 1: Email Opened → +5 score
        self.add_rule(AutomationRule(
            rule_id="rule_email_opened",
            trigger=TriggerType.EMAIL_OPENED,
            conditions={"segment": ["Standard", "VIP"]},
            actions=[
                AutomationAction(
                    action_type=ActionType.UPDATE_SCORE,
                    config={"score_delta": +5, "reason": "Email opened"}
                )
            ],
            priority=40,
            description="Increase score when email is opened"
        ))
        
        # Règle 2: Email Clicked → +15 score + Tag "engaged"
        self.add_rule(AutomationRule(
            rule_id="rule_email_clicked",
            trigger=TriggerType.EMAIL_CLICKED,
            conditions={"segment": ["Standard", "VIP"]},
            actions=[
                AutomationAction(
                    action_type=ActionType.UPDATE_SCORE,
                    config={"score_delta": +15, "reason": "Link clicked in email"}
                ),
                AutomationAction(
                    action_type=ActionType.ADD_TAG,
                    config={"tag": "engaged"},
                    delay_minutes=0
                )
            ],
            priority=60,
            description="High engagement: link click"
        ))
        
        # Règle 3: Email Bounce → Flag email invalide
        self.add_rule(AutomationRule(
            rule_id="rule_email_bounce",
            trigger=TriggerType.EMAIL_BOUNCE,
            actions=[
                AutomationAction(
                    action_type=ActionType.UPDATE_SCORE,
                    config={"score_delta": -20, "reason": "Email bounced"}
                ),
                AutomationAction(
                    action_type=ActionType.ADD_TAG,
                    config={"tag": "invalid_email"}
                )
            ],
            priority=80,
            description="Mark email as invalid on bounce"
        ))
        
        # Règle 4: Achat completé → VIP treatment
        self.add_rule(AutomationRule(
            rule_id="rule_purchase",
            trigger=TriggerType.PURCHASE,
            conditions={"minimum_amount": 50},
            actions=[
                AutomationAction(
                    action_type=ActionType.UPDATE_SCORE,
                    config={"score_delta": +50, "reason": "Purchase completed"}
                ),
                AutomationAction(
                    action_type=ActionType.SEND_EMAIL,
                    config={
                        "template": "thank_you",
                        "subject": "Merci pour votre achat!"
                    },
                    delay_minutes=5
                ),
                AutomationAction(
                    action_type=ActionType.CREATE_TASK,
                    config={"task": "Follow-up call"},
                    delay_minutes=1440  # 24h later
                )
            ],
            priority=90,
            description="Purchase workflow"
        ))
        
        # Règle 5: High score → VIP follow-up
        self.add_rule(AutomationRule(
            rule_id="rule_high_score",
            trigger=TriggerType.LEAD_SCORE_HIGH,
            conditions={"score_threshold": 80},
            actions=[
                AutomationAction(
                    action_type=ActionType.SEND_EMAIL,
                    config={
                        "template": "vip_offer",
                        "subject": "Offre VIP exclusive"
                    }
                ),
                AutomationAction(
                    action_type=ActionType.SCHEDULE_CALL,
                    config={"priority": "high"},
                    delay_minutes=120  # 2h later
                )
            ],
            priority=95,
            description="VIP lead nurturing"
        ))
        
        # Règle 6: Unsubscribe → Respect opt-out
        self.add_rule(AutomationRule(
            rule_id="rule_unsubscribe",
            trigger=TriggerType.UNSUBSCRIBE,
            actions=[
                AutomationAction(
                    action_type=ActionType.UPDATE_SCORE,
                    config={"score_delta": -100, "reason": "Unsubscribed"}
                ),
                AutomationAction(
                    action_type=ActionType.ADD_TAG,
                    config={"tag": "unsubscribed"}
                )
            ],
            priority=100,  # Highest priority
            description="Respect unsubscribe immediately"
        ))
        
        logger.info("✅ 6 default automation rules loaded")
    
    def add_rule(self, rule: AutomationRule):
        """
        Ajoute une règle d'automatisation
        
        Args:
            rule: AutomationRule
        """
        self.rules.append(rule)
        logger.debug(f"   Added rule: {rule.rule_id}")
    
    def get_applicable_rules(
        self,
        trigger: TriggerType,
        client_segment: Optional[str] = None,
        score: Optional[int] = None
    ) -> List[AutomationRule]:
        """
        Obtient les règles applicables pour un trigger donné
        
        Args:
            trigger: Type de déclencheur
            client_segment: Segment client (optionnel)
            score: Score client (optionnel)
        
        Returns:
            Liste de règles applicables, triées par priorité
        """
        applicable = []
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            # Vérifier trigger
            if rule.trigger != trigger:
                continue
            
            # Vérifier conditions
            if rule.conditions:
                # Vérifier segment si demandé
                if "segment" in rule.conditions and client_segment:
                    if client_segment not in rule.conditions["segment"]:
                        continue
                
                # Vérifier score minimum si demandé
                if "score_threshold" in rule.conditions and score:
                    if score < rule.conditions["score_threshold"]:
                        continue
            
            applicable.append(rule)
        
        # Trier par priorité (descendante)
        applicable.sort(key=lambda r: r.priority, reverse=True)
        
        return applicable
    
    def get_actions_for_event(
        self,
        trigger: TriggerType,
        client_segment: Optional[str] = None,
        score: Optional[int] = None
    ) -> List[AutomationAction]:
        """
        Obtient toutes les actions à exécuter pour un événement
        
        Args:
            trigger: Type déclencheur
            client_segment: Segment client
            score: Score client
        
        Returns:
            Liste d'actions à exécuter
        """
        rules = self.get_applicable_rules(trigger, client_segment, score)
        actions = []
        
        for rule in rules:
            actions.extend(rule.actions)
        
        return actions
    
    def save_rules(self, output_file: Optional[str] = None):
        """
        Sauvegarde les règles en JSON
        
        Args:
            output_file: Fichier de sortie
        """
        if not output_file:
            output_file = "exports/automation_rules.json"
        
        try:
            import os
            from pathlib import Path
            
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            
            rules_data = [rule.to_dict() for rule in self.rules]
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Rules sauvegardées: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde: {str(e)}")


class ScoreCalculator:
    """
    Calcule le score de lead dynamiquement
    """
    
    def __init__(self):
        """
        Initialise le calculateur
        """
        self.base_score = 50  # Score initial
    
    def calculate_score(
        self,
        rfm_score: float,
        engagement_events: int = 0,
        purchases: int = 0,
        days_since_purchase: int = 0
    ) -> int:
        """
        Calcule le score de lead global
        
        Args:
            rfm_score: Score RFM (0-4)
            engagement_events: Nombre d'événements engagement
            purchases: Nombre d'achats
            days_since_purchase: Jours depuis dernier achat
        
        Returns:
            Score global (0-100)
        """
        score = self.base_score
        
        # RFM contribution (max +40)
        score += int(rfm_score * 10)
        
        # Engagement contribution (max +20)
        score += min(engagement_events * 2, 20)
        
        # Purchase contribution (max +25)
        score += min(purchases * 5, 25)
        
        # Recency penalty (max -30)
        if days_since_purchase > 180:
            score -= 30
        elif days_since_purchase > 90:
            score -= 15
        elif days_since_purchase > 30:
            score -= 5
        
        # Cap score (0-100)
        return max(0, min(100, score))


if __name__ == '__main__':
    print("\n" + "="*70)
    print("  🪧 AUTOMATION RULES ENGINE")
    print("="*70 + "\n")
    
    # Initialiser moteur
    engine = AutomationRuleEngine()
    
    print(f"\n✅ {len(engine.rules)} rules loaded")
    
    # Exemple: Email ouvert
    print("\n1️⃣ Trigger: Email Opened")
    print("   Segment: VIP")
    actions = engine.get_actions_for_event(
        TriggerType.EMAIL_OPENED,
        client_segment="VIP"
    )
    for action in actions:
        print(f"   → {action.action_type.value}: {action.config}")
    
    # Exemple: Lien cliqué
    print("\n2️⃣ Trigger: Email Clicked")
    actions = engine.get_actions_for_event(
        TriggerType.EMAIL_CLICKED,
        client_segment="Standard"
    )
    for action in actions:
        print(f"   → {action.action_type.value}: {action.config}")
    
    # Exemple: Score calc
    print("\n3️⃣ Score Calculation")
    calculator = ScoreCalculator()
    score = calculator.calculate_score(
        rfm_score=3.5,
        engagement_events=5,
        purchases=3,
        days_since_purchase=10
    )
    print(f"   Score: {score}/100")
    
    # Sauvegarder
    print("\n4️⃣ Save rules")
    engine.save_rules()
    
    print("\n" + "="*70 + "\n")
