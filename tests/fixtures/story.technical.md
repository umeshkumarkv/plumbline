Cancel all open orders of one account in one action — stop further fills during a client incident

## User story
As an operations user handling a client incident / I want to cancel all open orders of one account in one action / So that no further fills happen while the incident is handled

## Today
Operations can cancel one order at a time; there is no account-level action.

## Acceptance criteria
- AC1: Given an account with orders that are new, validated, sent for execution or partly filled, When operations cancels all, Then every one of them is cancelled and operations sees how many were cancelled.
- AC2: Given an account that also has filled, cancelled or rejected orders, When operations cancels all, Then those orders are unchanged.
- AC3: POST /api/accounts/{id}/orders/cancel-all without OPERATIONS returns 403.
- AC4: Given an account number that does not exist, When operations cancels all, Then they are told the account was not found.
- AC5: Given an order that fills while cancel-all is running, When cancel-all finishes, Then operations sees that order listed as not cancelled, with the reason, and the other orders are cancelled.

## Examples
Account A: 3 new, 1 partly filled, 1 filled, 1 cancelled order → 4 cancelled. Account B: 1 new order → untouched.

## Out of scope
Several accounts at once; blocking new orders (kill switch); the screen button (separate story).

## Dependencies
Story points: 5

— Plumbline 2.8.3 · /pl-ba · story v1 · commit 2b87760 · judge pending · AI-drafted, posted after SME review
