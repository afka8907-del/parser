"""
Defect and issue detection from listing titles and descriptions.
"""

import re
from typing import Dict, List


class DefectDetector:
    """Detect defects, issues, and suspicious patterns in listings."""
    
    # Keywords for various issues (Romanian and English)
    DEFECT_PATTERNS = {
        "face_id_issue": [
            "face id", "faceid", "fata id", "faceid nu", "face-id",
            "nu functioneaza face", "face id stricat", "face id defect",
        ],
        "icloud_locked": [
            "icloud blocat", "icloud lock", "locked", "blocat icloud",
            "nu se deblocheaza", "cod uitat", "parola uitata",
            "apple id blocat", "cont blocat", "activation lock",
        ],
        "broken_display": [
            "display spart", "ecran spart", "sticla sparta", "display crapat",
            "touch defect", "nu merge touch", "display defect", "ecran defect",
            "linii pe display", "display cu puncte", "display nefunctional",
        ],
        "replaced_parts": [
            "display schimbat", "baterie schimbata", "inlocuit", "schimbat",
            "aftermarket", "copie", "replica", "non-original", "oem",
            "camera schimbata", "carcasa schimbata", "placa de baza",
        ],
        "battery_replaced": [
            "baterie schimbata", "baterie noua", "acumulator schimbat",
            "baterie inlocuita", "acumulator inlocuit", "battery replaced",
            "baterie aftermarket",
        ],
        "is_refurbished": [
            "refurbished", "refurb", "renovat", "reconditionat",
            "renewed", "restaurat", "ca nou", "like new", "refurbished",
        ],
        "is_fake": [
            "replica", "copie", "clona", "fake", "chinezesc",
            "nu e original", "nu este original", "imitatie", "clone",
        ],
    }
    
    SUSPICIOUS_PATTERNS = [
        "urgent", "urgenta", "foarte urgent", "ieftin", "super pret",
        "nu accept schimb", "doar cash", "nu verificat", "fara garantie",
        "nu am cutie", "fara accesorii", "fara incarcator", "fara cablu",
        "nu cunosc istoricul", "nu stiu istoricul", "nu cunosc originea",
        "vinde pentru prieten", "vand pentru cineva", "nu e al meu",
        "fara bon", "fara factura", "fara garantie", "as is", "pe componente",
    ]
    
    NEGOTIATION_INDICATORS = [
        "negociabil", "negociem", "discutabil", "discutam", "ofer pret",
        "accept oferte", "pret fix", "ultimul pret", "un mic discount",
        "mai las din pret", "pot negocia", "negociem usor",
    ]
    
    URGENCY_INDICATORS = [
        "urgent", "urgenta", "astazi", "maine", "saptamana asta",
        "plec din tara", "plec in", "am nevoie repede", "cash astazi",
        "super urgent", "oferta limitata", "nu stau mult",
    ]
    
    def analyze(self, title: str, description: str = "") -> Dict:
        """
        Analyze text for defects and issues.
        
        Returns:
            Dict with detection results
        """
        text = f"{title} {description}".lower()
        
        results = {}
        
        # Check for each defect type
        for defect_type, patterns in self.DEFECT_PATTERNS.items():
            results[defect_type] = self._check_patterns(text, patterns)
        
        # Check for suspicious patterns
        results["is_suspicious"] = self._check_patterns(text, self.SUSPICIOUS_PATTERNS)
        results["suspicious_reasons"] = self._get_matching_patterns(text, self.SUSPICIOUS_PATTERNS)
        
        # Check for negotiation probability
        results["negotiation_probability"] = self._check_patterns(text, self.NEGOTIATION_INDICATORS)
        
        # Check for urgency
        results["is_urgent"] = self._check_patterns(text, self.URGENCY_INDICATORS)
        results["urgency_reasons"] = self._get_matching_patterns(text, self.URGENCY_INDICATORS)
        
        # Estimate condition if not specified
        results["estimated_condition"] = self._estimate_condition(text, results)
        
        return results
    
    def _check_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if any pattern matches the text."""
        for pattern in patterns:
            if pattern in text:
                return True
        return False
    
    def _get_matching_patterns(self, text: str, patterns: List[str]) -> List[str]:
        """Get list of matching patterns."""
        matches = []
        for pattern in patterns:
            if pattern in text:
                matches.append(pattern)
        return matches
    
    def _estimate_condition(self, text: str, defect_results: Dict) -> str:
        """Estimate phone condition based on defects found."""
        defects_count = sum([
            defect_results.get("face_id_issue", False),
            defect_results.get("broken_display", False),
            defect_results.get("replaced_parts", False),
            defect_results.get("icloud_locked", False),
        ])
        
        # Look for condition keywords
        if "nou" in text or "sigilat" in text:
            return "new"
        elif "ca nou" in text or "impecabil" in text:
            return "like_new"
        elif defects_count == 0:
            return "good"
        elif defects_count <= 1:
            return "fair"
        else:
            return "poor"
    
    def extract_battery_health(self, text: str) -> int:
        """Extract battery health percentage from text."""
        patterns = [
            r"(\d+)\s*%?\s*(?:sanatate|health|baterie)",
            r"(?:sanatate|health|baterie).{0,20}(\d+)\s*%",
            r"battery\s*(?:health)?\s*(?:at)?\s*(\d+)\s*%",
            r"baterie\s*(\d+)%",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                value = int(match.group(1))
                if 0 <= value <= 100:
                    return value
        
        return None
    
    def extract_storage(self, text: str) -> int:
        """Extract storage capacity from text."""
        patterns = [
            r"(\d+)\s*(?:gb|go)",
            r"(\d+)\s*gb",
            r"(\d+)g",
            r"(\d+)\s+giga",
        ]
        
        common_sizes = [64, 128, 256, 512, 1024]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                value = int(match.group(1))
                if value in common_sizes or value >= 64:
                    return value
        
        return None
