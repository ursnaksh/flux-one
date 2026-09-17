import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.institution import Subject, Topic


SYLLABUS = {
    "IC2303": [
        (1, "LVDT Operating Principle & Characteristics"),
        (1, "Strain Gauges & Wheatstone Bridge"),
        (1, "Potentiometers & Optical Encoders"),
        (2, "Bourdon Tubes & Bellows"),
        (2, "Diaphragms & Piezoelectric Crystals"),
        (2, "Capacitive Pressure Transducers"),
        (3, "RTD (PT100) & Callendar-Van Dusen Formula"),
        (3, "Thermocouples & Seebeck Effect"),
        (3, "Thermistors & Optical Pyrometers"),
        (4, "Electromagnetic Flowmeters"),
        (4, "Ultrasonic Transceivers & Time-of-Flight"),
        (4, "Capacitive Level Probes"),
    ],
    "IC2301": [
        (1, "NumPy Array Computations & Vectorization"),
        (1, "Pandas DataFrames & Series"),
        (1, "Data Cleaning & Missing Value Imputation"),
        (2, "Matplotlib & Seaborn Visualizations"),
        (2, "Descriptive Statistics & Outlier Detection"),
        (2, "Correlation Heatmaps & Feature Selection"),
        (3, "Normal Distribution & Central Limit Theorem"),
        (3, "Hypothesis Testing (t-tests, z-tests)"),
        (3, "Confidence Intervals & p-values"),
        (4, "Linear Regression & Gradient Descent"),
        (4, "Logistic Regression for Classification"),
        (4, "Model Evaluation Metrics (RMSE, Accuracy, F1)"),
    ],
    "MM1408": [
        (1, "8051 Internal Memory Map & SFRs"),
        (1, "Pin Diagram & Oscillator Connections"),
        (1, "I/O Ports & Electrical Characteristics"),
        (2, "Addressing Modes (Immediate, Direct, Register)"),
        (2, "Data Transfer & Arithmetic Instructions"),
        (2, "Logical Operations & Branching"),
        (3, "8051 Timer Registers (TMOD, TCON)"),
        (3, "Timer Mode-1 (16-bit) & Mode-2 (8-bit Auto-reload)"),
        (3, "Interrupt Structure & Vector Locations"),
        (4, "ADC0808 / DAC0808 Interfacing"),
        (4, "16x2 LCD Display Command Sequencing"),
        (4, "Stepper Motor Driving via ULN2003"),
    ],
    "IC2305": [
        (1, "Classes, Objects & Encapsulation"),
        (1, "Constructors, Destructors & Copy Constructors"),
        (1, "Memory Management (new / delete)"),
        (2, "Single, Multiple & Multilevel Inheritance"),
        (2, "Function Overloading & Operator Overloading"),
        (2, "Virtual Functions & Pure Virtual Abstract Classes"),
        (3, "Function & Class Templates"),
        (3, "STL Vectors, Lists & Maps"),
        (3, "Iterators & Algorithms"),
        (4, "try, catch, throw Blocks"),
        (4, "Standard C++ File Streams"),
        (4, "Binary File Operations"),
    ],
    "IC2307": [
        (1, "Entity-Relationship (ER) Diagrams"),
        (1, "Relational Algebra & Relational Schema"),
        (1, "Primary, Foreign, & Composite Keys"),
        (2, "DDL, DML & DCL Commands"),
        (2, "Complex Subqueries & Nested SELECT"),
        (2, "INNER, LEFT, RIGHT & FULL OUTER Joins"),
        (3, "Functional Dependencies"),
        (3, "1NF, 2NF, 3NF Normal Forms"),
        (3, "Boyce-Codd Normal Form (BCNF)"),
        (4, "ACID Properties & Transaction States"),
        (4, "Serializability & Conflict Equivalence"),
        (4, "Two-Phase Locking (2PL) Protocol"),
    ],
    "HS2001": [
        (1, "Time, Speed & Distance Problems"),
        (1, "Percentages, Profit & Loss"),
        (1, "Permutations, Combinations & Probability"),
        (2, "Blood Relations & Direction Sense"),
        (2, "Syllogisms & Deductive Logic"),
        (2, "Seating Arrangement & Matrix Puzzles"),
    ],
    "IC2311": [
        (1, "User Empathy Mapping & Needfinding"),
        (1, "Problem Statement Framing (How Might We)"),
        (1, "Stakeholder Interview Analysis"),
        (2, "Brainstorming & SCAMPER Technique"),
        (2, "Low-Fidelity Hardware/Software Prototyping"),
        (2, "User Feedback & Iterative Testing"),
    ],
}


async def seed_syllabus_topics():
    async with AsyncSessionLocal() as db:
        created = 0
        for subject_code, topic_rows in SYLLABUS.items():
            result = await db.execute(select(Subject).where(Subject.code == subject_code))
            subject = result.scalar_one_or_none()
            if subject is None:
                continue

            existing_result = await db.execute(
                select(Topic.unit_number, Topic.title).where(Topic.subject_id == subject.id)
            )
            existing = {(row[0], row[1]) for row in existing_result.all()}

            for unit_number, title in topic_rows:
                if (unit_number, title) in existing:
                    continue
                db.add(
                    Topic(
                        subject_id=subject.id,
                        unit_number=unit_number,
                        title=title,
                        description=None,
                    )
                )
                created += 1

        await db.commit()
        print(f"Verified syllabus topics ready. Created {created} topics.")


if __name__ == "__main__":
    asyncio.run(seed_syllabus_topics())
