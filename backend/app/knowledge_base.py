"""
Knowledge Base -- WHO limits and gas health data.
Centralised so both threshold evaluation (MQTT subscriber) and API endpoints
can import from one place without circular dependencies.
"""

# WHO / OSHA safety limits per gas
# "limit" is the caution threshold (50% = YELLOW, 100% = RED)
WHO_LIMITS = {
    "LPG": {
        "limit": 1000.0,
        "unit": "ppm",
        "sensor_field": "mq2_ppm",
        "health_risks": ["Asphyxiation", "Explosion risk", "Narcotic effects at high concentration"],
        "safety_actions": ["Eliminate ignition sources", "Ventilate area", "Evacuate building"],
    },
    "CO": {
        "limit": 25.0,
        "unit": "ppm",
        "sensor_field": "mq7_ppm",
        "health_risks": ["Headache", "Dizziness", "Nausea", "Loss of consciousness", "Death at high concentrations"],
        "safety_actions": ["Evacuate area immediately", "Move to fresh air", "Call emergency services"],
    },
    "BENZENE": {
        "limit": 1.7,
        "unit": "ppm",
        "sensor_field": "mq135_ppm",
        "health_risks": ["Carcinogenic (Group 1)", "Bone marrow damage", "Leukemia risk", "Anemia"],
        "safety_actions": ["Wear respiratory protection", "Ensure ventilation", "Evacuate if level >5 ppm"],
    },
    "AMMONIA": {
        "limit": 25.0,
        "unit": "ppm",
        "sensor_field": "mq135_ppm",
        "health_risks": ["Severe eye burns", "Respiratory tract damage", "Pulmonary edema"],
        "safety_actions": ["Wear full PPE", "Ventilate enclosed spaces", "Flush eyes with water"],
    },
    "H2S": {
        "limit": 5.0,
        "unit": "ppm",
        "sensor_field": "mq136_ppm",
        "health_risks": ["Eye irritation", "Respiratory failure", "Pulmonary edema", "Death above 500 ppm"],
        "safety_actions": ["Leave area immediately", "Move upwind", "Use SCBA respirator", "Call hazmat team"],
    },
}

# Full gas info for API responses (knowledge base detail)
GAS_INFO = {
    "LPG": {
        "name": "Liquefied Petroleum Gas",
        "formula": "C3H8/C4H10",
        "sensor": "MQ-2",
        "who_limit": 1000.0,
        "unit": "ppm",
        "health_risks": WHO_LIMITS["LPG"]["health_risks"],
        "symptoms": ["Dizziness", "Nausea", "Difficulty breathing", "Loss of consciousness"],
        "safety_actions": WHO_LIMITS["LPG"]["safety_actions"],
        "source_devices": ["Aerosol cans in e-waste", "Refrigerant leaks", "Capacitor electrolyte"],
    },
    "CO": {
        "name": "Carbon Monoxide",
        "formula": "CO",
        "sensor": "MQ-7",
        "who_limit": 25.0,
        "unit": "ppm",
        "health_risks": WHO_LIMITS["CO"]["health_risks"],
        "symptoms": ["Headache", "Weakness", "Confusion", "Chest pain"],
        "safety_actions": WHO_LIMITS["CO"]["safety_actions"],
        "source_devices": ["Li-ion batteries", "PCB burning", "Plastic cable insulation", "Solder fumes"],
    },
    "BENZENE": {
        "name": "Benzene",
        "formula": "C6H6",
        "sensor": "MQ-135",
        "who_limit": 1.7,
        "unit": "ppm",
        "health_risks": WHO_LIMITS["BENZENE"]["health_risks"],
        "symptoms": ["Drowsiness", "Tremors", "Rapid heart rate", "Confusion"],
        "safety_actions": WHO_LIMITS["BENZENE"]["safety_actions"],
        "source_devices": ["CRT monitors", "Plastic housings", "Circuit boards", "PVC cables"],
    },
    "AMMONIA": {
        "name": "Ammonia",
        "formula": "NH3",
        "sensor": "MQ-135",
        "who_limit": 25.0,
        "unit": "ppm",
        "health_risks": WHO_LIMITS["AMMONIA"]["health_risks"],
        "symptoms": ["Pungent smell", "Tearing eyes", "Coughing", "Burning throat"],
        "safety_actions": WHO_LIMITS["AMMONIA"]["safety_actions"],
        "source_devices": ["Refrigerators", "Air conditioners", "Old cooling systems"],
    },
    "H2S": {
        "name": "Hydrogen Sulfide",
        "formula": "H2S",
        "sensor": "MQ-136",
        "who_limit": 5.0,
        "unit": "ppm",
        "health_risks": WHO_LIMITS["H2S"]["health_risks"],
        "symptoms": ["Rotten egg smell", "Eye burning", "Coughing", "Shortness of breath"],
        "safety_actions": WHO_LIMITS["H2S"]["safety_actions"],
        "source_devices": ["Lead-acid batteries", "Rubber components", "Sulfur-containing plastics"],
    },
    "CLEAN": {
        "name": "Clean Air",
        "formula": "N/A",
        "sensor": "All sensors",
        "who_limit": 0.0,
        "unit": "ppm",
        "health_risks": [],
        "symptoms": [],
        "safety_actions": ["No action required"],
        "source_devices": ["N/A"],
    },
}
