# Banking System Implementation

## Tier 1: Core Transaction Management

- ✅ Create an in-memory banking database system
- ✅ Implement basic CRUD operations for accounts
- ✅ Record and handle deposits and withdrawals
- ✅ Implement transfer functionality between accounts
- ✅ Ensure atomic operations (transfers must be accepted before processing)
- ✅ Support transaction logging

## Tier 2: Metrics

- Implement function that uses an efficient ranking algorithm to return top K accounts by:
  - Total transaction volume (deposits + withdrawals)
  - Total outgoing money

## Tier 3: Advanced Transaction Features

- Implement scheduled transactions system - can schedule a transaction at given time, and cancel it later

## Tier 4: Account Management

- Implement account merging functionality - merge two accounts while maintaining separate account histories
- Preserve separate transaction histories when merging, maintain data integrity during merges

## Follow-up Considerations

- How would you scale this system?
- How would you handle concurrent transactions?
- How would you implement disaster recovery?
- How would you optimize the ranking algorithm for large datasets?
- How would you ensure data consistency with scheduled transactions?
