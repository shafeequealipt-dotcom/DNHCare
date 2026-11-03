"""Bengaluru health calendar — what the weather is actually doing each month and
the complaints that come with it. The auto-picker used to give the model only
the month name, so it guessed the season (and kept writing about the monsoon in
November). This is the hand-checked source of truth instead; edit freely.
"""
import datetime

# month -> (weather phase, common complaints this month)
SEASONS = {
    1: ("cool, dry winter mornings",
        ["dry skin and eczema flares", "cracked heels", "dandruff", "cold and cough",
         "asthma", "sinusitis", "joint stiffness"]),
    2: ("dry and warming, dusty",
        ["pollen and dust allergies", "allergic rhinitis", "dry skin", "dandruff",
         "eye allergies"]),
    3: ("hot and dry",
        ["heat rash and prickly heat", "excess sweating", "dehydration headaches",
         "kidney stones", "urinary infections", "exam stress in children"]),
    4: ("hottest month",
        ["heat-triggered migraine", "fungal skin infections from sweat", "prickly heat",
         "kidney stones", "urinary infections", "acidity"]),
    5: ("hot, with pre-monsoon thunderstorms",
        ["heat exhaustion", "kidney stones", "urinary infections",
         "thunderstorm allergies and asthma", "early viral fevers"]),
    6: ("south-west monsoon onset",
        ["viral fever, cold and cough", "infections as schools reopen",
         "fungal infections", "mould allergies", "asthma"]),
    7: ("steady monsoon rain, damp",
        ["mould and dust-mite allergies", "fungal skin and nail infections",
         "viral fever", "joint pain in damp weather", "stomach upsets"]),
    8: ("monsoon, humid",
        ["viral and dengue fever season", "fungal infections", "eczema in humidity",
         "stomach upsets from water", "sinusitis"]),
    9: ("monsoon tailing off",
        ["dengue and viral fever", "allergies", "fungal infections",
         "post-viral weakness", "tonsillitis in children"]),
    10: ("north-east monsoon, festival season",
         ["post-viral cough", "allergies", "acidity from festival food",
          "sinusitis", "dengue tail"]),
    11: ("north-east monsoon ending, turning cool",
         ["festival smoke and poor air: asthma and allergic cough", "sinusitis",
          "post-viral cough", "dry skin starting", "tonsillitis in children"]),
    12: ("cool, dry, misty mornings",
         ["colds and tonsillitis in children", "asthma", "dry skin and eczema",
          "dandruff and hair fall", "joint stiffness", "acidity from holiday food"]),
}


def for_month(month: int) -> tuple:
    """(phase, complaints) for a month number."""
    return SEASONS[month]


def brief(day: datetime.date | None = None) -> str:
    """One prompt-ready paragraph describing Bengaluru's season on `day`."""
    day = day or datetime.date.today()
    phase, complaints = SEASONS[day.month]
    return (f"It is {day.strftime('%B')} {day.year} in Bengaluru: {phase}. Health "
            f"concerns common right now: {', '.join(complaints)}.")
