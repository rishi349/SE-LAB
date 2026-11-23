### TBD Updates and Ongoing Design Decisions

The team is currently investigating and evaluating the following pending dependencies and architectural decisions:

1. **Authentication and Authorization:** Evaluating JWT (JSON Web Tokens) and OAuth 2.0 for implementing secure authentication and authorization mechanisms.
    
2. **Transaction Architecture:** Exploring the transaction architecture and determining how financial transactions will be structured, processed, and managed while maintaining consistency and atomicity.
    
3. **Initial Wallet Funding:** Considering an admin-controlled fund allocation mechanism for the initial funding of user wallets. The corresponding transactions will be recorded in the double-entry ledger.
    
4. **Security APIs:** Identifying and evaluating the APIs and endpoints required for authentication, authorization, token validation, and secure access control.
    
5. **GraphQL Evaluation:** Investigating whether GraphQL would be beneficial for the project and evaluating its suitability against the proposed REST-based architecture.
    
6. **REST vs. GraphQL for Authentication:** After considering the security and architectural implications, the team has decided to proceed with REST-based endpoints for login and authentication. The overall API design and implementation approach are still being explored.
    
7. **Implementation Planning:** The team is currently evaluating the implementation strategies, dependencies, and integration requirements to finalize the system architecture before proceeding with development.
    

These items are currently under investigation and will be finalized as part of the design and implementation planning phase.



need to plan the low level design
1)ATOMIC
2)SYCHRONOUS 
3)CONSISTENCY
4)SECURITY 
5)TESTING(CI/CD)
6)no ACCOUN T AND ZERO BALNACED ACCOUNT SHOULD BE SEPERATED
7)DESIGN FOR TESTABILITY 
8)SHOULD NOT GIVE FLOATING POINT ERRORS 

WORK DIVIDING
0)BACKEND-RISHi
1)security-RISHI,ROHIT
2_)databsae-hansdling-THARUN ,PRAMOD
N)design for testability-ROHIT
transaction handling-combined(TBD)


financial-ledger-api/
├── app/
│   ├── main.py
│   ├── routers/
│   ├── services/
│   ├── database/
│   ├── models/
│   └── schemas/
├── tests/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md

phase 4)**Financial Transaction Management**- rohit 
phase 5)**API Management**-Rishi


