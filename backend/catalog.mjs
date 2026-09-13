// Class data migrated from the existing timetable/calendar and practice library.
// Versioned seed: existing database records change only when this version increases.
export const catalogSeed = {
  "id": "sy-ic-seda-2026-sem1",
  "version": 1,
  "class_name": "SY IC-SEDA",
  "academic_year": "2026–27",
  "semester": "I",
  "sources": {
    "timetable": "Updated_SY-D_TT.pdf",
    "calendar": "Academic Calendar_DSE_SEDA_BTECH__A.Y. 2026-27_Sem_I.pdf",
    "practice": "Suggested practice topics and quizzes; verify coverage against your course syllabus."
  },
  "courses": [
    {
      "id": "sat",
      "code": "IC2303",
      "tag": "SAT",
      "name": "Sensors and Transducers",
      "faculty": "Prof. Seema S. Mashalkar (SSM)",
      "color": "cyan",
      "units": [
        {
          "name": "Unit 1: Motion & Displacement",
          "topics": [
            "LVDT Operating Principle & Characteristics",
            "Strain Gauges & Wheatstone Bridge",
            "Potentiometers & Optical Encoders"
          ]
        },
        {
          "name": "Unit 2: Pressure & Force",
          "topics": [
            "Bourdon Tubes & Bellows",
            "Diaphragms & Piezoelectric Crystals",
            "Capacitive Pressure Transducers"
          ]
        },
        {
          "name": "Unit 3: Temperature Sensors",
          "topics": [
            "RTD (PT100) & Callendar-Van Dusen Formula",
            "Thermocouples & Seebeck Effect",
            "Thermistors & Optical Pyrometers"
          ]
        },
        {
          "name": "Unit 4: Flow & Level Sensors",
          "topics": [
            "Electromagnetic Flowmeters",
            "Ultrasonic Transceivers & Time-of-Flight",
            "Capacitive Level Probes"
          ]
        }
      ]
    },
    {
      "id": "ds",
      "code": "IC2301",
      "tag": "DS",
      "name": "Data Science",
      "faculty": "Prof. Rajesh Pashikanti (RP)",
      "color": "blue",
      "units": [
        {
          "name": "Unit 1: Python for Data Science",
          "topics": [
            "NumPy Array Computations & Vectorization",
            "Pandas DataFrames & Series",
            "Data Cleaning & Missing Value Imputation"
          ]
        },
        {
          "name": "Unit 2: Exploratory Data Analysis",
          "topics": [
            "Matplotlib & Seaborn Visualizations",
            "Descriptive Statistics & Outlier Detection",
            "Correlation Heatmaps & Feature Selection"
          ]
        },
        {
          "name": "Unit 3: Statistical Inference",
          "topics": [
            "Normal Distribution & Central Limit Theorem",
            "Hypothesis Testing (t-tests, z-tests)",
            "Confidence Intervals & p-values"
          ]
        },
        {
          "name": "Unit 4: Supervised Learning",
          "topics": [
            "Linear Regression & Gradient Descent",
            "Logistic Regression for Classification",
            "Model Evaluation Metrics (RMSE, Accuracy, F1)"
          ]
        }
      ]
    },
    {
      "id": "maa",
      "code": "MM1408",
      "tag": "MAA",
      "name": "Microcontroller & Applications",
      "faculty": "Prof. Pramod M. Kanjalkar (PMK)",
      "color": "purple",
      "units": [
        {
          "name": "Unit 1: 8051 Architecture",
          "topics": [
            "8051 Internal Memory Map & SFRs",
            "Pin Diagram & Oscillator Connections",
            "I/O Ports & Electrical Characteristics"
          ]
        },
        {
          "name": "Unit 2: Instruction Set & Assembly",
          "topics": [
            "Addressing Modes (Immediate, Direct, Register)",
            "Data Transfer & Arithmetic Instructions",
            "Logical Operations & Branching"
          ]
        },
        {
          "name": "Unit 3: Timers & Interrupts",
          "topics": [
            "8051 Timer Registers (TMOD, TCON)",
            "Timer Mode-1 (16-bit) & Mode-2 (8-bit Auto-reload)",
            "Interrupt Structure & Vector Locations"
          ]
        },
        {
          "name": "Unit 4: Hardware Interfacing",
          "topics": [
            "ADC0808 / DAC0808 Interfacing",
            "16x2 LCD Display Command Sequencing",
            "Stepper Motor Driving via ULN2003"
          ]
        }
      ]
    },
    {
      "id": "oop",
      "code": "IC2305",
      "tag": "OOP",
      "name": "Object Oriented Programming",
      "faculty": "Prof. Sheetal M. Katwe (SMK)",
      "color": "emerald",
      "units": [
        {
          "name": "Unit 1: OOP Fundamentals",
          "topics": [
            "Classes, Objects & Encapsulation",
            "Constructors, Destructors & Copy Constructors",
            "Memory Management (new / delete)"
          ]
        },
        {
          "name": "Unit 2: Inheritance & Polymorphism",
          "topics": [
            "Single, Multiple & Multilevel Inheritance",
            "Function Overloading & Operator Overloading",
            "Virtual Functions & Pure Virtual Abstract Classes"
          ]
        },
        {
          "name": "Unit 3: Templates & STL",
          "topics": [
            "Function & Class Templates",
            "STL Vectors, Lists & Maps",
            "Iterators & Algorithms"
          ]
        },
        {
          "name": "Unit 4: Exception Handling & File I/O",
          "topics": [
            "try, catch, throw Blocks",
            "Standard C++ File Streams",
            "Binary File Operations"
          ]
        }
      ]
    },
    {
      "id": "dbms",
      "code": "IC2307",
      "tag": "DBMS",
      "name": "Database Management Systems",
      "faculty": "Prof. Vikas J. Nandeshwar (VJN)",
      "color": "amber",
      "units": [
        {
          "name": "Unit 1: Relational Modeling",
          "topics": [
            "Entity-Relationship (ER) Diagrams",
            "Relational Algebra & Relational Schema",
            "Primary, Foreign, & Composite Keys"
          ]
        },
        {
          "name": "Unit 2: SQL Mastery",
          "topics": [
            "DDL, DML & DCL Commands",
            "Complex Subqueries & Nested SELECT",
            "INNER, LEFT, RIGHT & FULL OUTER Joins"
          ]
        },
        {
          "name": "Unit 3: Normalization",
          "topics": [
            "Functional Dependencies",
            "1NF, 2NF, 3NF Normal Forms",
            "Boyce-Codd Normal Form (BCNF)"
          ]
        },
        {
          "name": "Unit 4: Transactions & Concurrency",
          "topics": [
            "ACID Properties & Transaction States",
            "Serializability & Conflict Equivalence",
            "Two-Phase Locking (2PL) Protocol"
          ]
        }
      ]
    },
    {
      "id": "raad",
      "code": "HS2001",
      "tag": "RAAD",
      "name": "Reasoning & Aptitude Development - 3",
      "faculty": "Prof. Manisha P. Narwane (MPN)",
      "color": "rose",
      "units": [
        {
          "name": "Unit 1: Quantitative Aptitude",
          "topics": [
            "Time, Speed & Distance Problems",
            "Percentages, Profit & Loss",
            "Permutations, Combinations & Probability"
          ]
        },
        {
          "name": "Unit 2: Logical Reasoning",
          "topics": [
            "Blood Relations & Direction Sense",
            "Syllogisms & Deductive Logic",
            "Seating Arrangement & Matrix Puzzles"
          ]
        }
      ]
    },
    {
      "id": "dt",
      "code": "IC2311",
      "tag": "DT-1",
      "name": "Design Thinking - 1",
      "faculty": "Dr. Jayant Kulkarni / Prof. S. Waghmare",
      "color": "indigo",
      "units": [
        {
          "name": "Unit 1: Empathy & Problem Definition",
          "topics": [
            "User Empathy Mapping & Needfinding",
            "Problem Statement Framing (How Might We)",
            "Stakeholder Interview Analysis"
          ]
        },
        {
          "name": "Unit 2: Ideation & Prototyping",
          "topics": [
            "Brainstorming & SCAMPER Technique",
            "Low-Fidelity Hardware/Software Prototyping",
            "User Feedback & Iterative Testing"
          ]
        }
      ]
    }
  ],
  "timetable": [
    "Mon|11:00 - 12:00 PM|Theory|Microcontroller & Applications (MM1408)|PMK|C204|ALL|maa|0|0",
    "Mon|12:00 - 01:00 PM|Theory|Sensors & Transducers (IC2303)|SSM|C204|ALL|sat|0|0",
    "Mon|01:00 - 03:00 PM|Lab|Data Science Lab (IC2301)|RP|C304|B2|ds|0|1",
    "Mon|03:00 - 05:00 PM|Lab|OOP Lab (IC2305)|SMK|C304|B2|oop|0|0",
    "Mon|03:00 - 05:00 PM|Lab|Sensors & Transducers Lab (IC2303)|SSM|C307|B1|sat|0|0",
    "Mon|03:00 - 05:00 PM|Lab|Data Science Lab (IC2301)|RP|C305|B3|ds|0|1",
    "Mon|05:00 - 06:00 PM|Tutorial|Design Thinking - 1 Tutorial (IC2311)|JVK|TBA|B1|dt|0|0",
    "Mon|05:00 - 07:00 PM|Lab|Data Science Lab (IC2301)|RP|C304|B1|ds|0|1",
    "Mon|05:00 - 07:00 PM|Lab|Sensors & Transducers Lab (IC2303)|SSM|C307|B2|sat|0|0",
    "Tue|11:00 - 12:00 PM|Theory|Microcontroller & Applications (MM1408)|PMK|C301|ALL|maa|0|0",
    "Tue|12:00 - 01:00 PM|Theory|Database Management Systems (IC2307)|VJN|C301|ALL|dbms|0|0",
    "Tue|01:00 - 02:00 PM|Theory|Object Oriented Programming (IC2305)|SMK|C301|ALL|oop|0|0",
    "Tue|04:00 - 06:00 PM|Lab|Data Science Lab (IC2301)|RP|C304|B1|ds|0|1",
    "Tue|04:00 - 06:00 PM|Lab|Sensors & Transducers Lab (IC2303)|SSM|C307|B2|sat|0|0",
    "Wed|12:00 - 02:00 PM|Lab|OOP Lab (IC2305)|SMK|C308|B3|oop|0|0",
    "Wed|02:00 - 03:00 PM|Theory|Sensors & Transducers (IC2303)|SSM|C301|ALL|sat|0|0",
    "Wed|03:00 - 04:00 PM|Tutorial|Design Thinking - 1 Tutorial (IC2311)|JVK|C314|B2|dt|0|0",
    "Wed|04:00 - 05:00 PM|Tutorial|Microcontroller & Applications Tutorial (MM1408)|PMK|C314|B5|maa|0|0",
    "Wed|04:00 - 06:00 PM|Lab|Database Management Systems Lab (IC2307)|VJN|C305|B3|dbms|0|0",
    "Thu|09:00 - 11:00 AM|Lab|OOP Lab (IC2305)|SMK|C308|B1|oop|0|0",
    "Thu|12:00 - 01:00 PM|Tutorial|Microcontroller & Applications Tutorial (MM1408)|PMK|C314|B4|maa|0|0",
    "Thu|01:00 - 02:00 PM|Theory|Sensors & Transducers (IC2303)|SSM|C204|ALL|sat|0|0",
    "Thu|03:00 - 04:00 PM|Theory|Data Science (IC2301)|RP|C301|ALL|ds|0|0",
    "Thu|04:00 - 06:00 PM|Lab|Database Management Systems Lab (IC2307)|VJN|C305|B1|dbms|0|0",
    "Fri|10:00 - 11:00 AM|Theory|Reasoning & Aptitude Development - 3 (HS2001)|MPN|C204|ALL|raad|0|0",
    "Fri|11:00 - 12:00 PM|Tutorial|Design Thinking - 1 Tutorial (IC2311)|SVW|TBA|B3|dt|0|0",
    "Fri|01:00 - 02:00 PM|Theory|Database Management Systems (IC2307)|VJN|C204|ALL|dbms|0|0",
    "Fri|02:00 - 03:00 PM|Theory|Object Oriented Programming (IC2305)|SMK|C301|ALL|oop|0|0",
    "Fri|03:00 - 04:00 PM|Theory|Data Science (IC2301)|RP|C301|ALL|ds|0|0",
    "Fri|04:00 - 06:00 PM|Lab|Database Management Systems Lab (IC2307)|VJN|C305|B2|dbms|0|0",
    "Fri|04:00 - 06:00 PM|Lab|Sensors & Transducers Lab (IC2303)|SSM|C307|B3|sat|0|0"
  ],
  "milestones": [
    {
      "title": "Semester commencement",
      "start": "2026-08-24",
      "end": "2026-08-24"
    },
    {
      "title": "Mid-Semester Examination & Reviews",
      "start": "2026-10-26",
      "end": "2026-10-31"
    },
    {
      "title": "Internal Assessment (GD/PPT, CP)",
      "start": "2026-12-07",
      "end": "2026-12-12"
    },
    {
      "title": "End of Semester",
      "start": "2026-12-12",
      "end": "2026-12-12"
    },
    {
      "title": "End-Semester Examination",
      "start": "2026-12-14",
      "end": "2026-12-26"
    },
    {
      "title": "Tentative start of next semester",
      "start": "2027-01-04",
      "end": "2027-01-04"
    }
  ],
  "holidays": [
    {
      "title": "Shri Ganesh Chaturthi",
      "date": "2026-09-14"
    },
    {
      "title": "Gauri Pujan",
      "date": "2026-09-18"
    },
    {
      "title": "Anant Chaturdashi",
      "date": "2026-09-25"
    },
    {
      "title": "Mahatma Gandhi Jayanti",
      "date": "2026-10-02"
    }
  ],
  "quizzes": {
    "sat": [
      {
        "q": "In an LVDT, what is the output voltage at the null (center) position theoretically?",
        "options": [
          "Maximum AC voltage",
          "Zero volts",
          "Pure DC offset voltage",
          "Equal to excitation voltage"
        ],
        "ans": 1,
        "exp": "At the null position, secondary voltages are identical in amplitude and 180° out of phase, canceling each other out to zero."
      },
      {
        "q": "Which transducer operates on the piezoelectric effect for dynamic pressure?",
        "options": [
          "Quartz / PZT Crystal",
          "Copper Wire",
          "Silicon Thermistor",
          "Nichrome Coil"
        ],
        "ans": 0,
        "exp": "PZT crystals generate charge proportional to applied mechanical strain."
      }
    ],
    "maa": [
      {
        "q": "What is the register bit width of the DPTR in an 8051 microcontroller?",
        "options": [
          "8-bit",
          "16-bit",
          "32-bit",
          "4-bit"
        ],
        "ans": 1,
        "exp": "DPTR is a 16-bit register composed of DPH and DPL, used to address external memory."
      }
    ],
    "ds": [
      {
        "q": "In Pandas, what is the key difference between .loc[] and .iloc[]?",
        "options": [
          ".loc is label-based, .iloc is integer position-based",
          ".loc is for columns only",
          ".iloc is deprecated",
          "There is no difference"
        ],
        "ans": 0,
        "exp": ".loc references index names or labels, while .iloc strictly indexes by 0-based integer positions."
      }
    ]
  }
};

