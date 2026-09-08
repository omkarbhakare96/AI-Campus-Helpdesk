"""
generate_dataset.py
Generates a realistic dataset of 300+ college complaints for the
AI-Based Campus Helpdesk system, saved to dataset/complaints.csv

Columns: complaint_text, category, priority, sentiment
"""

import csv
import random
import os

random.seed(42)

# ---------------------------------------------------------------------------
# Category -> list of (text_template, priority, sentiment) building blocks
# We build many variations by combining subjects/objects/locations with
# templates, so the final dataset has 300+ realistic, non-duplicate rows.
# ---------------------------------------------------------------------------

# Each issue is tagged with an explicit priority so that severity language
# in the text (fire, shock, hazard, days, weeks, etc.) is a genuine,
# learnable signal for the priority-prediction model rather than random noise.
CATEGORIES = {
    "IT/Network": {
        "subjects": ["Wi-Fi", "the internet connection", "the college portal", "the LMS website",
                     "the computer lab network", "the printer server", "the campus Wi-Fi router",
                     "the exam portal", "the email server", "the biometric login system"],
        "issues": [
            ("is extremely slow and keeps disconnecting every few minutes", "Medium"),
            ("has not been working since morning and I cannot access any online resources", "High"),
            ("is completely down in the entire block", "Critical"),
            ("shows an error every time I try to log in", "Low"),
            ("keeps timing out when uploading assignments", "Medium"),
            ("is not accessible from the hostel rooms", "Medium"),
            ("crashed while I was submitting my online exam", "Critical"),
            ("has very weak signal in the library section", "Low"),
            ("is asking for a password that was never issued to me", "Low"),
            ("has been malfunctioning for the past three days", "High"),
        ],
    },
    "Infrastructure": {
        "subjects": ["the classroom door", "the ceiling fan in room 204", "the projector in the seminar hall",
                     "the window glass in the physics lab", "the staircase railing", "the lecture hall bench",
                     "the false ceiling panel", "the classroom lighting", "the auditorium sound system",
                     "the corridor flooring"],
        "issues": [
            ("is broken and needs immediate repair", "High"),
            ("has been damaged for weeks and no one has fixed it", "Medium"),
            ("is not working properly during lectures", "Medium"),
            ("fell down and could injure students", "Critical"),
            ("is cracked and unsafe to use", "Critical"),
            ("makes a loud noise and disturbs the class", "Low"),
            ("has loose wiring hanging out", "Critical"),
            ("is completely non-functional", "High"),
            ("was damaged during the last storm and remains unrepaired", "Medium"),
            ("needs urgent maintenance before it collapses", "Critical"),
        ],
    },
    "Laboratory": {
        "subjects": ["the chemistry lab equipment", "the computer lab systems", "the physics lab apparatus",
                     "the microscopes in the biology lab", "the lab exhaust fan", "the electronics lab kits",
                     "the lab safety gear", "the oscilloscope in the electronics lab", "the lab computers",
                     "the workshop machinery"],
        "issues": [
            ("are outdated and frequently malfunction during practicals", "Medium"),
            ("are not sufficient for the number of students in the batch", "Low"),
            ("have not been serviced in a long time", "Medium"),
            ("are missing important components required for the experiment", "Medium"),
            ("pose a safety hazard to students", "Critical"),
            ("are damaged and unusable", "High"),
            ("have not been replaced despite multiple requests", "Medium"),
            ("are extremely slow, wasting practical session time", "Low"),
            ("lack proper safety instructions posted nearby", "High"),
            ("need urgent calibration as readings are inaccurate", "High"),
        ],
    },
    "Library": {
        "subjects": ["the library reading room", "the book issue counter", "the library Wi-Fi",
                     "the reference section", "the digital library access", "the library AC",
                     "the library seating arrangement", "the library staff", "the book renewal system",
                     "the newspaper section"],
        "issues": [
            ("closes earlier than the notified timings", "Low"),
            ("does not have enough copies of the prescribed textbooks", "Medium"),
            ("is too noisy to study in", "Low"),
            ("has not updated the catalog with new arrivals", "Low"),
            ("charges an unfair fine despite timely return", "Medium"),
            ("has broken chairs and tables", "Medium"),
            ("is not accessible online from outside the campus", "Medium"),
            ("staff was rude while assisting with a book search", "High"),
            ("lacks proper lighting for late evening study", "Low"),
            ("system shows incorrect due dates for borrowed books", "Medium"),
        ],
    },
    "Hostel": {
        "subjects": ["the hostel water supply", "the hostel mess food", "the hostel room fan",
                     "the hostel washroom", "the hostel Wi-Fi", "the hostel warden",
                     "the hostel room cleanliness", "the hostel gate timing", "the hostel bed and furniture",
                     "the hostel laundry service"],
        "issues": [
            ("has not been available for the past two days", "High"),
            ("quality has degraded badly and causes stomach issues", "Critical"),
            ("is not working and the room becomes unbearably hot", "Medium"),
            ("is not cleaned regularly and smells bad", "Medium"),
            ("signal does not reach the upper floors", "Low"),
            ("is not responding to repeated complaints", "High"),
            ("was not addressed despite the pest control request", "High"),
            ("is too early and inconvenient for students with late labs", "Low"),
            ("is broken and needs replacement", "Medium"),
            ("is delayed and clothes are often lost", "Low"),
        ],
    },
    "Transport": {
        "subjects": ["the college bus", "the shuttle service", "the bus driver", "the bus route schedule",
                     "the bus pass renewal process", "the parking area for two-wheelers",
                     "the bus conductor", "the evening bus timing", "the bus seating capacity",
                     "the bus AC"],
        "issues": [
            ("is always late by more than 30 minutes", "Medium"),
            ("is overcrowded beyond safe capacity", "High"),
            ("drives rashly endangering student safety", "Critical"),
            ("was cancelled without any prior notice", "High"),
            ("does not cover our residential area anymore", "Medium"),
            ("is not functioning even in peak summer", "Low"),
            ("process takes too many days to complete", "Low"),
            ("area is poorly lit and unsafe at night", "High"),
            ("was rude to students who asked about the delay", "Medium"),
            ("skipped our stop without waiting", "Medium"),
        ],
    },
    "Electricity": {
        "subjects": ["the power supply in the boys hostel", "the classroom lights", "the lab power sockets",
                     "the corridor lighting", "the electricity in the girls hostel", "the generator backup",
                     "the wiring near the canteen", "the streetlights on campus", "the power supply in the library",
                     "the switchboard in room 105"],
        "issues": [
            ("keeps tripping every few hours", "Medium"),
            ("has been out for the entire day", "High"),
            ("sockets are sparking and dangerous to use", "Critical"),
            ("flickers constantly, damaging appliances", "Medium"),
            ("backup does not switch on during outages", "High"),
            ("wiring is exposed and could cause a fire", "Critical"),
            ("have not worked for the last week making it dark at night", "High"),
            ("voltage fluctuates and damages electronic devices", "Medium"),
            ("switchboard gives mild shocks when touched", "Critical"),
            ("was never restored after the recent short circuit", "Critical"),
        ],
    },
    "Cleanliness": {
        "subjects": ["the boys washroom", "the girls washroom", "the canteen area", "the classroom floors",
                     "the college corridors", "the dustbins near the parking lot", "the drainage near the hostel",
                     "the water cooler area", "the sports ground", "the staircase area"],
        "issues": [
            ("has not been cleaned for several days", "Medium"),
            ("smells extremely bad and is unhygienic", "High"),
            ("is littered with garbage all over", "Low"),
            ("overflowed and water is stagnant, breeding mosquitoes", "High"),
            ("have not been emptied in over a week", "Medium"),
            ("is filled with dust and cobwebs", "Low"),
            ("has broken taps causing water wastage and mess", "Medium"),
            ("is infested with stray animals", "High"),
            ("was not sanitized after the recent illness outbreak", "Critical"),
            ("needs immediate attention from housekeeping staff", "Medium"),
        ],
    },
    "Examination": {
        "subjects": ["the exam timetable", "the hall ticket portal", "the answer sheet evaluation",
                     "the exam seating arrangement", "the internal marks upload", "the revaluation process",
                     "the exam hall ventilation", "the online exam system", "the exam invigilator",
                     "the result declaration"],
        "issues": [
            ("has scheduling conflicts between two subjects", "High"),
            ("is not generating hall tickets for several students", "Critical"),
            ("seems incorrect and needs to be rechecked", "Medium"),
            ("was chaotic and roll numbers were misplaced", "High"),
            ("was not completed before the deadline", "High"),
            ("takes far too long with no updates given", "Medium"),
            ("is poor and students feel suffocated during exams", "Medium"),
            ("logged me out in the middle of the exam", "Critical"),
            ("behaved unfairly with several students", "High"),
            ("has been delayed without any official communication", "Medium"),
        ],
    },
    "Administration": {
        "subjects": ["the fee payment portal", "the scholarship application process", "the certificate issuance counter",
                     "the admission office staff", "the ID card renewal process", "the bonafide certificate request",
                     "the transcript request process", "the accounts department", "the student affairs office",
                     "the migration certificate process"],
        "issues": [
            ("is not accepting payments due to a technical error", "High"),
            ("has been pending for over a month without any update", "Medium"),
            ("staff is uncooperative and unresponsive to queries", "Medium"),
            ("gave incorrect information leading to confusion", "Low"),
            ("takes an unusually long time to process", "Low"),
            ("lost my submitted documents", "Critical"),
            ("charges hidden fees that were not communicated earlier", "Medium"),
            ("is not answering calls or emails", "Low"),
            ("rejected my application without a valid reason", "High"),
            ("requires the same documents to be submitted repeatedly", "Low"),
        ],
    },
    "Security": {
        "subjects": ["the main gate security", "the CCTV monitoring", "the hostel entry security",
                     "the parking lot security", "the campus security guards", "the visitor entry process",
                     "the night security patrol", "the ID verification at the gate", "the emergency alarm system",
                     "the security near the girls hostel"],
        "issues": [
            ("allowed unauthorized outsiders to enter without checking IDs", "Critical"),
            ("cameras have not been working for weeks", "High"),
            ("is lax and anyone can walk in after hours", "High"),
            ("reported a theft that was never investigated", "Critical"),
            ("guards are often missing from their posts", "Medium"),
            ("does not verify visitors properly, raising safety concerns", "High"),
            ("is irregular and the campus feels unsafe at night", "High"),
            ("is not being done at all at the back gate", "Medium"),
            ("did not respond during a recent fire drill", "Critical"),
            ("needs strengthening after the recent incident", "Critical"),
        ],
    },
    "Other": {
        "subjects": ["the notice board updates", "the student feedback process", "the college website",
                     "the event registration system", "the sports equipment", "the canteen food quality",
                     "the college app", "the alumni portal", "the student council elections",
                     "the general grievance redressal process"],
        "issues": [
            ("is outdated and shows wrong information", "Low"),
            ("does not seem to be taken seriously by the management", "Medium"),
            ("has broken links and outdated content", "Low"),
            ("closed before I could register for the event", "Medium"),
            ("is old, damaged and needs replacement", "Medium"),
            ("has deteriorated and is often stale", "Low"),
            ("keeps crashing on both Android and iOS", "Medium"),
            ("has not been updated for the current batch", "Low"),
            ("was conducted without proper transparency", "High"),
            ("does not provide any timeline for resolution", "Low"),
        ],
    },
}

OPENERS = [
    "I want to report that",
    "This is to bring to your notice that",
    "I am writing to complain that",
    "Respected Sir/Madam,",
    "I would like to inform you that",
    "Kindly look into the issue that",
    "",
    "To whomsoever it may concern,",
    "I am extremely disappointed that",
    "It has come to my attention that",
]

CLOSERS = [
    "Please resolve this at the earliest.",
    "Kindly take necessary action as soon as possible.",
    "I request immediate attention to this matter.",
    "This is causing a lot of inconvenience to students.",
    "Please fix this issue soon.",
    "I hope this gets resolved quickly.",
    "This needs urgent attention from the concerned department.",
    "",
    "Thank you for looking into this.",
    "I would appreciate a quick response.",
]

NEGATIVE_WORDS = ["extremely", "very", "completely", "totally", "absolutely", "seriously"]

POSITIVE_TEMPLATES = [
    "I just wanted to appreciate that {subj} was fixed quickly and works great now, thank you!",
    "Great job by the staff, {subj} has improved a lot recently and I am satisfied.",
    "Thanks to the quick response team, {subj} issue was resolved smoothly and I am happy with the service.",
    "I am pleased to note that {subj} has been upgraded and is working perfectly now.",
    "Excellent support was given when I reported an issue with {subj}, really appreciate the effort.",
]

NEUTRAL_TEMPLATES = [
    "Could you please provide an update regarding {subj}? Just checking on the status.",
    "I have a query about {subj}, please let me know the current process.",
    "Requesting information on {subj} for my reference, not urgent.",
    "Wanted to confirm the schedule/details related to {subj} when convenient.",
    "Please share the standard procedure for {subj} whenever possible.",
]


def sentiment_for(priority):
    if priority == "Critical":
        return random.choices(["Negative", "Neutral"], weights=[0.9, 0.1])[0]
    if priority == "High":
        return random.choices(["Negative", "Neutral"], weights=[0.75, 0.25])[0]
    if priority == "Medium":
        return random.choices(["Negative", "Neutral", "Positive"], weights=[0.55, 0.35, 0.10])[0]
    return random.choices(["Negative", "Neutral", "Positive"], weights=[0.35, 0.40, 0.25])[0]


def build_complaint(category, data):
    subj = random.choice(data["subjects"])
    issue, priority = random.choice(data["issues"])
    sentiment = sentiment_for(priority)

    if sentiment == "Positive":
        text = random.choice(POSITIVE_TEMPLATES).format(subj=subj)
    elif sentiment == "Neutral" and random.random() < 0.5:
        # Occasionally phrase even a real issue as a neutral status query
        text = random.choice(NEUTRAL_TEMPLATES).format(subj=subj)
    else:
        opener = random.choice(OPENERS)
        closer = random.choice(CLOSERS)
        intensifier = random.choice(NEGATIVE_WORDS) if random.random() < 0.5 else ""
        sentence = f"{subj} {intensifier} {issue}".replace("  ", " ").strip()
        sentence = sentence[0].upper() + sentence[1:]
        parts = [p for p in [opener, sentence + ".", closer] if p]
        text = " ".join(parts)

    return text, category, priority, sentiment


def main():
    rows = []
    # Ensure at least 25 samples per category (12 categories * 25 = 300)
    per_category = 30
    for category, data in CATEGORIES.items():
        seen = set()
        count = 0
        attempts = 0
        while count < per_category and attempts < 500:
            attempts += 1
            text, cat, priority, sentiment = build_complaint(category, data)
            if text in seen:
                continue
            seen.add(text)
            rows.append([text, cat, priority, sentiment])
            count += 1

    random.shuffle(rows)

    out_path = os.path.join(os.path.dirname(__file__), "dataset", "complaints.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["complaint_text", "category", "priority", "sentiment"])
        writer.writerows(rows)

    print(f"Generated {len(rows)} complaint records -> {out_path}")


if __name__ == "__main__":
    main()
