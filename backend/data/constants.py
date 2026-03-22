"""
Shared constants used across data generation modules.
"""

AD_CATEGORIES = ["tech", "food", "auto", "fashion", "finance", "travel", "health", "gaming"]

AGE_GROUPS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]

# Rough age-group distribution for a streaming platform audience.
AGE_GROUP_WEIGHTS = [0.18, 0.26, 0.22, 0.16, 0.11, 0.07]

GENRES = [
    "Action",
    "Comedy",
    "Drama",
    "Sci-Fi",
    "Horror",
    "Documentary",
    "Romance",
    "Thriller",
    "Animation",
    "Fantasy",
]

PROFESSIONS = [
    "Software Engineer",
    "Teacher",
    "Designer",
    "Doctor",
    "Student",
    "Manager",
    "Writer",
    "Nurse",
    "Accountant",
    "Freelancer",
    "Retired",
    "Marketing Specialist",
    "Data Analyst",
    "Sales Representative",
    "Lawyer",
]

SEASONS = ["Spring", "Summer", "Fall", "Winter"]

CONTENT_MOODS = ["calm", "uplifting", "playful", "energetic", "intense", "dark"]

TIME_OF_DAY_VALUES = ["morning", "afternoon", "evening", "latenight"]

ADVERTISERS = {
    "tech": ["TechPulse", "GadgetHub", "CloudNine", "PixelBridge", "DataFlow"],
    "food": ["FreshBite", "TasteWorld", "SnapEats", "GourmetBox", "NomNom"],
    "auto": ["DriveForward", "AutoZen", "RoadKing", "SwiftWheels", "GreenDrive"],
    "fashion": ["StyleNest", "TrendVault", "ChicLine", "UrbanThread", "GlowWear"],
    "finance": ["WealthPath", "SafeVault", "GrowFunds", "TrustBank", "PrimeSave"],
    "travel": ["WanderLux", "AirNomad", "TripStar", "RoamFree", "SkyBound"],
    "health": ["VitaCore", "FitPulse", "NaturaMed", "WellPath", "ClearMind"],
    "gaming": ["PlayVerse", "LevelUp", "PixelRealm", "ArenaX", "QuestHub"],
}
