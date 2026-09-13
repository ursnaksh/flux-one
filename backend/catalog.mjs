// Official VIT Pune Curriculum Pattern B25
// Version 2 ensures fresh cache invalidation for deep topics and subtopics
export const catalogSeed = {
  "id": "sy-ic-seda-2026-sem1",
  "version": 2,
  "class_name": "SY IC-SEDA",
  "academic_year": "2026–27",
  "semester": "I",
  "sources": {
    "timetable": "Updated_SY-D_TT.pdf",
    "calendar": "Academic Calendar_DSE_SEDA_BTECH__A.Y. 2026-27_Sem_I.pdf",
    "practice": "Official VIT Pune Syllabus Pattern B25 (AY 2025-26 / 2026-27)"
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
          "name": "Unit 1: Basic Measurement Systems & Displacement Sensors",
          "topics": [
            "Measurement System Fundamentals: Process components, static & dynamic characteristics, calibration standards",
            "Potentiometric Transducers: Equivalent circuits, loading effect, charge and voltage sensitivity",
            "Inductive Sensors: LVDT, RVDT, variable reluctance, self & mutual inductance principles",
            "Strain Gauges & Load Cells: Gauge factor, bridge circuits, pneumatic, hydraulic and electronic load cells"
          ]
        },
        {
          "name": "Unit 2: Digital Transducers, Speed & Proximity Measurement",
          "topics": [
            "Digital Encoders: Translational and rotary optical encoders, gray code vs binary encoding",
            "Proximity Pickups: Inductive, capacitive, optical, ultrasonic, Hall-Effect and magnetic sensors",
            "Flapper-Nozzle Mechanism: Deflection sensitivity, pneumatic nozzle characteristics and applications",
            "Speed Measurement & Analytical Sensors: AC/DC tachometers, stroboscopes, toothed rotor, pH and conductivity"
          ]
        },
        {
          "name": "Unit 3: Temperature Measurement Systems",
          "topics": [
            "Temperature Scales & Mechanical Sensors: Units, bimetallic thermometers and thermal expansion",
            "Resistance Temperature Detectors (RTD): PT100 construction, Callendar-Van Dusen equation, 2/3/4 lead-wire compensation",
            "Thermocouples: Laws of thermoelectricity (Seebeck, Peltier, Thomson), cold junction compensation, types (J, K, R, S, T)",
            "Thermistors & Pyrometry: NTC and PTC thermistors, bridge linearization, thermopiles and thermowell design"
          ]
        },
        {
          "name": "Unit 4: Flow Measurement Systems",
          "topics": [
            "Fluid Statics & Dynamics: Newtonian vs Non-Newtonian fluids, Reynolds number, velocity profile, Bernoulli theorem",
            "Head Type Flowmeters: Orifice plates (concentric, eccentric, segmental), taps, venturi tube, Pitot tube",
            "Variable Area Meters: Rotameter operating principle, float equilibrium, beta ratio and density correction",
            "Velocity & Mass Meters: Turbine flowmeters, electromagnetic flowmeters, ultrasonic Doppler/transit-time, hot-wire anemometers"
          ]
        },
        {
          "name": "Unit 5: Pressure Measurement & Calibration",
          "topics": [
            "Manometers & Elastic Sensors: U-tube, inclined manometers, C-type Bourdon tube, corrugated diaphragms, bellows",
            "High & Differential Pressure Transducers: Bulk modulus cell, capacitance delta cell, force balance DP transmitters",
            "Vacuum Measurement: Thermal conductivity Pirani gauges, thermocouple gauges, McLeod gauge",
            "Pressure Calibration Standards: Dead Weight Tester operation, vacuum tester calibration procedures"
          ]
        },
        {
          "name": "Unit 6: Level Measurement Techniques",
          "topics": [
            "Direct Sight Gauges: Hook type gauges, tubular, transparent and reflex sight glasses",
            "Hydrostatic & Bubbler Systems: Hydrostatic head level measurement, air purge (bubbler) systems",
            "Displacer & Float Transmitters: Displacer torque-tube units, magnetic float switches, float and tape systems",
            "Non-Contact & Solid Level Sensing: Ultrasonic level transceivers, Guided Wave Radar (TDR/PDS), capacitive probes, radioactive methods"
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
          "name": "Unit 1: Data Science Pipeline & Preprocessing",
          "topics": [
            "Data Science Architecture: Raw data, processed data, metadata, attributes and end-to-end data pipeline",
            "Data Cleaning & Feature Engineering: Missing value imputation, noise handling, outlier treatment, normalization"
          ]
        },
        {
          "name": "Unit 2: Probability Distributions & Statistical Inference",
          "topics": [
            "Probability Distributions: Normal distribution, Binomial distribution, evaluation and standard normal variate",
            "Inferential Statistics: Central Limit Theorem, confidence intervals, hypothesis testing, p-value analysis"
          ]
        },
        {
          "name": "Unit 3: Mathematical Foundations & Optimization",
          "topics": [
            "Vector Spaces & Norms: L1 and L2 norms, distance metrics in multi-dimensional feature space",
            "Optimization Techniques: Unconstrained optimization, gradient descent algorithms, loss function minimization"
          ]
        },
        {
          "name": "Unit 4: Regression Modeling & Prediction",
          "topics": [
            "Linear Regression: Simple and multiple linear regression, ordinary least squares, coefficient estimation",
            "Logistic & Non-Linear Regression: Logistic regression for classification, decision boundaries, polynomial regression"
          ]
        },
        {
          "name": "Unit 5: Supervised & Unsupervised Machine Learning",
          "topics": [
            "Nearest Neighbor & Bayesian Classification: KNN classifier, Branch and Bound, Naïve Bayes probabilistic model",
            "Decision Trees & Clustering: ID3/CART decision trees, K-Means clustering, divisive and agglomerative hierarchical clustering"
          ]
        },
        {
          "name": "Unit 6: Model Evaluation & Validation Techniques",
          "topics": [
            "Classification Performance Metrics: Confusion matrix, sensitivity, specificity, precision, recall, F1-score, ROC-AUC",
            "Model Validation Strategies: Resubstitution, hold-out method, K-fold cross-validation, bootstrapping"
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
          "name": "Unit 1: 8051 Architecture & Memory Organization",
          "topics": [
            "8051 Internal Hardware Architecture: ALU, accumulator, B register, Program Status Word, stack pointer",
            "Memory Map: Internal RAM structure (register banks, bit-addressable RAM, scratchpad), Program ROM, Special Function Registers (SFRs)",
            "Pin Configuration & Hardware Interface: Oscillator connections, machine cycle timing, reset circuitry, I/O ports P0-P3"
          ]
        },
        {
          "name": "Unit 2: 8051 Instruction Set & Assembly Programming",
          "topics": [
            "Addressing Modes: Immediate, register, direct, register-indirect, and indexed addressing modes",
            "Instruction Set: Data transfer, arithmetic (ADD, SUBB, MUL, DIV), logical (ANL, ORL, XRL) and bit manipulation instructions",
            "Branching & Subroutines: Unconditional jumps (SJMP, LJMP), conditional jumps (CJNE, DJNZ, JZ, JNZ), CALL and RET execution"
          ]
        },
        {
          "name": "Unit 3: Timers, Counters & Interrupt Controller",
          "topics": [
            "8051 Timers & Counters: TMOD and TCON registers, Mode 0 (13-bit), Mode 1 (16-bit), Mode 2 (8-bit auto-reload)",
            "Delay Generation & Frequency Calculation: Timer programming in C and Assembly, baud rate generation for serial ports",
            "Interrupt Architecture: Interrupt vector table, IE and IP registers, external hardware interrupts (INT0, INT1), timer and serial interrupts"
          ]
        },
        {
          "name": "Unit 4: Serial Communication & Peripheral Interfacing",
          "topics": [
            "UART Serial Communication: SCON, SBUF registers, RS232 standard, MAX232 level shifter interfacing",
            "ADC & DAC Interfacing: ADC0808/0809 successive approximation ADC and DAC0808 R-2R ladder interfacing",
            "Industrial Actuators & Display: 16x2 LCD display command sequencing, 4x4 matrix keypad scanning, stepper motor control via ULN2003"
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
          "name": "Unit 1: Java OOP Fundamentals, Memory & I/O",
          "topics": [
            "OOP Principles: Encapsulation, abstraction, classes, objects, Java memory storage (heap vs stack)",
            "Class Mechanics: Static vs instance variables/methods/blocks, access modifiers, 'this' keyword, constructors (default, parameterized)",
            "Java I/O System: Byte stream vs character stream, java.util.Scanner class for console input"
          ]
        },
        {
          "name": "Unit 2: Arrays, Strings & Method Architectures",
          "topics": [
            "Java Arrays: Initialization, default values, multi-dimensional arrays, java.util.Arrays utility functions",
            "String Handling: String immutability, memory pool, StringBuffer, StringBuilder performance comparison",
            "Method Mechanics: Call-by-value, passing and returning objects, returning multiple values"
          ]
        },
        {
          "name": "Unit 3: Inheritance & Polymorphism",
          "topics": [
            "Inheritance Architecture: Types of inheritance, 'super' keyword, constructor chaining in inheritance, final keyword",
            "Polymorphism: Method overloading, static vs dynamic binding, method hiding, method overriding"
          ]
        },
        {
          "name": "Unit 4: Exception Handling, Interfaces & Inner Classes",
          "topics": [
            "Exception Handling: Checked vs unchecked exceptions, try-catch-finally blocks, throw vs throws, custom user-defined exceptions",
            "Interfaces & Abstract Classes: Abstract classes vs interfaces, multiple interface implementation, default/static interface methods",
            "Inner Classes: Member inner classes, static nested classes, local inner classes, anonymous inner classes"
          ]
        },
        {
          "name": "Unit 5: Collections Framework & Multithreading",
          "topics": [
            "Java Collections Framework: ArrayList, Vector, LinkedList, HashSet, TreeSet, HashMap, TreeMap, Iterators vs for-each",
            "Multithreading Architecture: Thread lifecycle, Thread class vs Runnable interface, thread priorities, thread synchronization, inter-thread communication"
          ]
        },
        {
          "name": "Unit 6: File Processing, JDBC & Swing GUI",
          "topics": [
            "File Streams & Serialization: FileInputStream/FileOutputStream, FileReader/FileWriter, object serialization (Serializable)",
            "Database Connectivity (JDBC): JDBC architecture, Driver types, Connection, Statement, PreparedStatement, ResultSet processing",
            "Java Swing GUI: JFrame, JPanel, Layout Managers (Flow, Border, Grid, Card), event delegation model (ActionListener, MouseListener)"
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
          "name": "Unit 1: DBMS Architecture & Data Modeling",
          "topics": [
            "DBMS Fundamentals: Three-schema architecture, data independence, DBMS vs file systems, database design process",
            "Entity-Relationship (ER) Model: Entities, attributes (simple, composite, multivalued), relationships, cardinality & participation constraints",
            "Extended ER (EER) & Relational Mapping: Generalization, specialization, aggregation, mapping ER to relational schema",
            "Relational Model: Relational integrity constraints, foreign keys, Codd's 12 rules"
          ]
        },
        {
          "name": "Unit 2: Relational Database Design & Normalization",
          "topics": [
            "Functional Dependencies: Inference rules (Armstrong's axioms), attribute closure, canonical minimal cover",
            "Decomposition Properties: Lossless-join decomposition, dependency-preserving decomposition",
            "Normal Forms: First (1NF), Second (2NF), Third (3NF) Normal Forms, Boyce-Codd Normal Form (BCNF)",
            "Higher Normal Forms: Multi-valued dependencies and Fourth Normal Form (4NF)"
          ]
        },
        {
          "name": "Unit 3: Relational Algebra, SQL & PL/SQL",
          "topics": [
            "Relational Algebra: Selection, projection, cartesian product, set operations, rename, natural join, theta join, outer joins",
            "SQL Query Language: DDL, DML, DCL, TCL commands, integrity constraints (PK, FK, CHECK, UNIQUE)",
            "Advanced SQL: Aggregate functions, GROUP BY, HAVING, subqueries (correlated and uncorrelated), joins",
            "PL/SQL Programming: Stored procedures, functions, explicit and implicit cursors, row-level and statement-level triggers"
          ]
        },
        {
          "name": "Unit 4: Storage, Indexing & Query Processing",
          "topics": [
            "Physical Storage: File organization, fixed-length vs variable-length records, buffer pool management",
            "Indexing Structures: Primary indexes, clustering indexes, secondary indexes, dense vs sparse indexes",
            "Tree-Structured Indexing: B-Trees and B+ Trees (search, insert, delete operations)",
            "Query Processing & Optimization: Query parsing, relational algebra equivalence rules, cost-based query optimization"
          ]
        },
        {
          "name": "Unit 5: Transaction Management & Concurrency Control",
          "topics": [
            "Transaction Concepts: ACID properties, transaction states, schedules and concurrent execution",
            "Serializability: Conflict serializability, precedence graphs, view serializability",
            "Concurrency Control Protocols: Two-Phase Locking (2PL), Strict 2PL, Rigorous 2PL, Timestamp-ordering protocol",
            "Deadlock & Recovery: Deadlock prevention (Wait-Die, Wound-Wait), deadlock detection, Write-Ahead Logging (WAL) and checkpoint recovery"
          ]
        },
        {
          "name": "Unit 6: Distributed, NoSQL & Data Warehousing",
          "topics": [
            "Distributed Databases: Distributed database architecture, data fragmentation (horizontal/vertical), data replication",
            "NoSQL Databases & Big Data: Key-Value, Document-based (MongoDB), Columnar, Graph databases, CAP theorem, BASE properties",
            "Data Warehousing: Data warehouse architecture, OLTP vs OLAP, dimensional modeling (Star schema, Snowflake schema)"
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
          "name": "Unit 1: English Language & Verbal Ability",
          "topics": [
            "Vocabulary Building: Synonyms, antonyms, contextual vocabulary, idioms and phrasal verbs",
            "Grammar & Syntax: Error identification, sentence improvement, active/passive voice, direct/indirect speech",
            "Reading Comprehension: Passage analysis, paragraph completion, critical verbal reasoning"
          ]
        },
        {
          "name": "Unit 2: Logical & Deductive Reasoning",
          "topics": [
            "Deductive Logic: Syllogisms, coding-decoding, blood relations, directional sense",
            "Analytical Reasoning: Seating arrangements (linear, circular), matrix selection tables, logical puzzles",
            "Inductive & Abductive Reasoning: Number and letter series, analogies, data sufficiency"
          ]
        },
        {
          "name": "Unit 3: Quantitative Aptitude",
          "topics": [
            "Arithmetic Foundations: Divisibility, HCF/LCM, fractions, decimals, surds and indices",
            "Commercial Arithmetic: Percentages, profit and loss, ratios, proportions, simple and compound interest",
            "Applied Mathematics: Time, speed and distance, time and work, mixtures and alligations",
            "Modern Mathematics: Permutations, combinations, probability distributions, data interpretation (charts/tables)"
          ]
        }
      ]
    },
    {
      "id": "dt",
      "code": "IC2236",
      "tag": "DT-1",
      "name": "Design Thinking - 1",
      "faculty": "Dr. Jayant Kulkarni / Prof. S. Waghmare",
      "color": "indigo",
      "units": [
        {
          "name": "Unit 1: Research Methodology & Scientific Publishing",
          "topics": [
            "Research Foundations: Research definition, problem identification, literature review methodologies",
            "Research Paper Architecture: Title, abstract, introduction, system architecture, methodology, results and discussion",
            "Journal Metrics & Evaluation: Journal indexing (Scopus, Web of Science), impact factor, H-index, paper submission process",
            "Research Ethics: Academic integrity, plagiarism checking tools, citation standards (IEEE style)"
          ]
        },
        {
          "name": "Unit 2: Intellectual Property Rights & Patent Drafting",
          "topics": [
            "IPR Overview: Patents, trademarks, copyrights, trade secrets, design registrations",
            "Patent Searching & Prior Art: Patent databases, novelty analysis, non-obviousness criteria",
            "Patent Drafting & Filing: Complete and provisional specifications, claims drafting, patent filing procedure and examination responses",
            "Entrepreneurship: Translating research and patents into engineering startups and business models"
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
    "Mon|05:00 - 06:00 PM|Tutorial|Design Thinking - 1 Tutorial (IC2236)|JVK|TBA|B1|dt|0|0",
    "Mon|05:00 - 07:00 PM|Lab|Data Science Lab (IC2301)|RP|C304|B1|ds|0|1",
    "Mon|05:00 - 07:00 PM|Lab|Sensors & Transducers Lab (IC2303)|SSM|C307|B2|sat|0|0",
    "Tue|11:00 - 12:00 PM|Theory|Microcontroller & Applications (MM1408)|PMK|C301|ALL|maa|0|0",
    "Tue|12:00 - 01:00 PM|Theory|Database Management Systems (IC2307)|VJN|C301|ALL|dbms|0|0",
    "Tue|01:00 - 02:00 PM|Theory|Object Oriented Programming (IC2305)|SMK|C301|ALL|oop|0|0",
    "Tue|04:00 - 06:00 PM|Lab|Data Science Lab (IC2301)|RP|C304|B1|ds|0|1",
    "Tue|04:00 - 06:00 PM|Lab|Sensors & Transducers Lab (IC2303)|SSM|C307|B2|sat|0|0",
    "Wed|12:00 - 02:00 PM|Lab|OOP Lab (IC2305)|SMK|C308|B3|oop|0|0",
    "Wed|02:00 - 03:00 PM|Theory|Sensors & Transducers (IC2303)|SSM|C301|ALL|sat|0|0",
    "Wed|03:00 - 04:00 PM|Tutorial|Design Thinking - 1 Tutorial (IC2236)|JVK|C314|B2|dt|0|0",
    "Wed|04:00 - 05:00 PM|Tutorial|Microcontroller & Applications Tutorial (MM1408)|PMK|C314|B5|maa|0|0",
    "Wed|04:00 - 06:00 PM|Lab|Database Management Systems Lab (IC2307)|VJN|C305|B3|dbms|0|0",
    "Thu|09:00 - 11:00 AM|Lab|OOP Lab (IC2305)|SMK|C308|B1|oop|0|0",
    "Thu|12:00 - 01:00 PM|Tutorial|Microcontroller & Applications Tutorial (MM1408)|PMK|C314|B4|maa|0|0",
    "Thu|01:00 - 02:00 PM|Theory|Sensors & Transducers (IC2303)|SSM|C204|ALL|sat|0|0",
    "Thu|03:00 - 04:00 PM|Theory|Data Science (IC2301)|RP|C301|ALL|ds|0|0",
    "Thu|04:00 - 06:00 PM|Lab|Database Management Systems Lab (IC2307)|VJN|C305|B1|dbms|0|0",
    "Fri|10:00 - 11:00 AM|Theory|Reasoning & Aptitude Development - 3 (HS2001)|MPN|C204|ALL|raad|0|0",
    "Fri|11:00 - 12:00 PM|Tutorial|Design Thinking - 1 Tutorial (IC2236)|SVW|TBA|B3|dt|0|0"
  ]
};
