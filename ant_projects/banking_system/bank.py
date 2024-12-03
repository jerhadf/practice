import threading
from collections import deque
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, NonNegativeFloat, field_validator


class InsufficientFundsError(Exception):
    def __init__(self, new_balance: float, account_id: int):
        super().__init__(f"Insufficient funds error: new balance {new_balance} would be <0 for account_id {account_id}")


class AccountNotFoundError(Exception):
    def __init__(self, account_id: int):
        super().__init__(f"Get account failed: no account exists for ID {account_id}")


class TransactionKind(str, Enum):
    CREATION = "creation"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"


class Transaction(BaseModel):
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="ISO 8601 UTC timestamp of when transaction occurred",
    )
    kind: TransactionKind = Field(
        ...,
        description=f"Kind of transaction, one of: {', '.join(t.value for t in TransactionKind)}",
    )
    amount: float = Field(..., description="Amount of transaction in $USD")
    balance_after: float = Field(..., description="Balance after transaction completed in $USD")


class BankAccount(BaseModel):
    """Stores account details and transaction history."""

    account_id: int = Field(..., description="Account ID, unique integer", ge=0)
    owner: str = Field(..., description="Account owner's name", min_length=1)
    balance: NonNegativeFloat = Field(..., description="Account balance in $USD")
    transaction_log: deque[Transaction] = deque(maxlen=None)

    @field_validator("owner")
    def owner_validator(self, v):
        """Validates that the owner name is not empty."""
        if not v or v == "":
            raise ValueError("owner cannot be empty")
        return v


class Bank:
    def __init__(self):
        # in memory-database: banks store accounts, which map IDs to account details
        self.accounts: dict[int, BankAccount] = {}
        self.curr_id: int = 0  # uuids are just ints, which increment up over time
        # locks
        self.account_locks: dict[int, threading.Lock] = {}
        self.global_lock = threading.Lock()  # lock for all accounts modifications

    def create_account(self, owner: str, starting_balance: float) -> BankAccount:
        """Create bank account with owner and balance, using IDs as account identifiers"""
        with self.global_lock:  #  only allow modifying 1 account in dict at a time
            account_id = self.curr_id
            self.curr_id += 1
            self.account_locks[account_id] = threading.Lock()  # lock for this account
            starting_transaction = Transaction(
                kind=TransactionKind.CREATION,
                amount=starting_balance,
                balance_after=starting_balance,
            )
            account = BankAccount(
                owner=owner,
                balance=starting_balance,
                account_id=account_id,
                transaction_log=deque([starting_transaction]),
            )
            self.accounts[account_id] = account

        print(f"Account {account_id} created successfully for {owner} with balance ${starting_balance}")
        return self.accounts[account_id]

    def read_account(self, account_id: int) -> BankAccount:
        """Return the BankAccount for account with ID - read-only"""
        if account_id not in self.accounts:
            raise AccountNotFoundError(account_id)
        return self.accounts[account_id]

    def read_all_accounts(self) -> dict[int, BankAccount]:
        """Return all of the bank accounts in the bank - read-only"""
        return self.accounts

    def deposit(self, account_id: int, amount: float) -> float:
        """Add a positive amount to the specified account ID"""
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        if account_id not in self.accounts:
            raise AccountNotFoundError(account_id)
        with self.account_locks[account_id]:  # 1 transaction for account at a time
            new_balance = self.accounts[account_id].balance + amount
            self.accounts[account_id].balance = new_balance
            self.accounts[account_id].transaction_log.append(
                Transaction(
                    kind=TransactionKind.DEPOSIT,
                    amount=amount,
                    balance_after=new_balance,
                )
            )
            print(f"Deposited ${amount} to account {account_id}. New balance: ${new_balance}")
            return new_balance

    def withdraw(self, account_id: int, amount: float) -> float:
        """Subtract a positive amount from the specified account ID"""
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")
        if account_id not in self.accounts:
            raise AccountNotFoundError(account_id)
        with self.account_locks[account_id]:  # 1 transaction for account at a time
            new_balance = self.accounts[account_id].balance - amount
            if new_balance < 0:
                raise InsufficientFundsError(new_balance, account_id)
            self.accounts[account_id].balance = new_balance
            self.accounts[account_id].transaction_log.append(
                Transaction(
                    kind=TransactionKind.WITHDRAWAL,
                    amount=-amount,
                    balance_after=new_balance,
                )
            )
            print(f"Withdrew ${amount} from account {account_id}. New balance: ${new_balance}")
            return new_balance

    def delete_account(self, account_id: int) -> bool:
        """Delete account with given ID. Returns True if successful."""
        if account_id not in self.accounts:
            raise AccountNotFoundError(account_id)
        with self.global_lock:
            del self.accounts[account_id]
            del self.account_locks[account_id]
            return True

    def transfer(self, from_account_id: int, to_account_id: int, amount: float) -> tuple[float, float]:
        """Transfer money between accounts, returning the new balances of both accounts."""
        if from_account_id == to_account_id:
            raise ValueError(f"Transfer failed: cannot transfer from account {from_account_id} to itself")
        if amount <= 0:
            raise ValueError(f"Transfer failed: transfer amount {amount} must be positive")
        with self.global_lock:  # only allow 1 transfer at a time
            # verify accounts exist before proceeding
            if from_account_id not in self.accounts:
                raise AccountNotFoundError(from_account_id)
            if to_account_id not in self.accounts:
                raise AccountNotFoundError(to_account_id)
            if self.accounts[from_account_id].balance < amount:
                raise InsufficientFundsError(self.accounts[from_account_id].balance - amount, from_account_id)

        # perform the transfer atomically
        try:
            from_account = self.accounts[from_account_id]
            to_account = self.accounts[to_account_id]

            from_account.balance -= amount
            to_account.balance += amount

            from_account.transaction_log.append(
                Transaction(
                    kind=TransactionKind.TRANSFER,
                    amount=-amount,
                    balance_after=from_account.balance,
                )
            )

            to_account.transaction_log.append(
                Transaction(
                    kind=TransactionKind.TRANSFER,
                    amount=amount,
                    balance_after=to_account.balance,
                )
            )

            print(
                f"Successfully transferred ${amount} from account {from_account_id} "
                f"(new balance: ${from_account.balance}) to {to_account_id} "
                f"(new balance: ${to_account.balance})"
            )

            return (from_account.balance, to_account.balance)

        except Exception as e:
            # if anything fails, roll back the changes
            if "from_account" in locals():
                from_account.balance += amount  # restore original balance
            raise ValueError(f"Transfer failed: {str(e)}")

    def get_top_accounts_by_volume(self, k: int) -> list[tuple[int, float]]:
        """Returns top K accounts by total transaction volume (deposits + withdrawals).
        Returns list of tuples (account_id, volume) sorted by volume descending."""
        if k <= 0:
            raise ValueError("k must be positive")

        account_volumes = []
        for account_id, account in self.accounts.items():
            volume = sum(abs(t.amount) for t in account.transaction_log)
            account_volumes.append((account_id, volume))

        return sorted(account_volumes, key=lambda x: x[1], reverse=True)[:k]

    def get_top_accounts_by_outgoing(self, k: int) -> list[tuple[int, float]]:
        """Returns top K accounts by total outgoing money (withdrawals + transfers out).
        Returns list of tuples (account_id, outgoing_amount) sorted by amount descending."""
        if k <= 0:
            raise ValueError("k must be positive")

        account_outgoing = []
        for account_id, account in self.accounts.items():
            outgoing = sum(
                abs(t.amount) for t in account.transaction_log
                if t.amount < 0 and t.kind in (TransactionKind.WITHDRAWAL,
                                               TransactionKind.TRANSFER)
            )
            account_outgoing.append((account_id, outgoing))

        return sorted(account_outgoing, key=lambda x: x[1], reverse=True)[:k]
