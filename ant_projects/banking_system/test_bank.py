import threading
import unittest

from bank import AccountNotFoundError, Bank, InsufficientFundsError, TransactionKind


class TestBank(unittest.TestCase):
    def setUp(self):
        self.bank = Bank()

    def test_create_account(self):
        # Test basic account creation
        account = self.bank.create_account("John Doe", 1000.0)
        self.assertEqual(account.owner, "John Doe")
        self.assertEqual(account.balance, 1000.0)
        self.assertEqual(account.account_id, 0)
        self.assertEqual(len(account.transaction_log), 1)
        self.assertEqual(account.transaction_log[0].kind, TransactionKind.CREATION)

    def test_create_account_validation(self):
        # Test invalid inputs
        with self.assertRaises(ValueError):
            self.bank.create_account("", 1000.0)
        with self.assertRaises(ValueError):
            self.bank.create_account("John Doe", -100.0)

        # Test sequential ID assignment
        acc1 = self.bank.create_account("User1", 100.0)
        acc2 = self.bank.create_account("User2", 200.0)
        self.assertEqual(acc1.account_id, 0)
        self.assertEqual(acc2.account_id, 1)

    def test_read_account(self):
        # Test successful read
        account = self.bank.create_account("Jane Doe", 500.0)
        read_account = self.bank.read_account(0)
        self.assertEqual(read_account.owner, "Jane Doe")
        self.assertEqual(read_account.balance, 500.0)

        # Test reading non-existent account
        with self.assertRaises(AccountNotFoundError):
            self.bank.read_account(999)

    def test_read_all_accounts(self):
        # Test empty bank
        self.assertEqual(len(self.bank.read_all_accounts()), 0)

        # Test multiple accounts
        self.bank.create_account("User1", 100.0)
        self.bank.create_account("User2", 200.0)
        accounts = self.bank.read_all_accounts()
        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts[0].owner, "User1")
        self.assertEqual(accounts[1].owner, "User2")

    def test_deposit(self):
        account = self.bank.create_account("Test User", 1000.0)

        # Test successful deposit
        new_balance = self.bank.deposit(0, 500.0)
        self.assertEqual(new_balance, 1500.0)
        self.assertEqual(len(account.transaction_log), 2)
        self.assertEqual(account.transaction_log[-1].kind, TransactionKind.DEPOSIT)

        # Test invalid deposits
        with self.assertRaises(ValueError):
            self.bank.deposit(0, -100.0)
        with self.assertRaises(ValueError):
            self.bank.deposit(0, 0)
        with self.assertRaises(AccountNotFoundError):
            self.bank.deposit(999, 100.0)

    def test_withdraw(self):
        account = self.bank.create_account("Test User", 1000.0)

        # Test successful withdrawal
        new_balance = self.bank.withdraw(0, 500.0)
        self.assertEqual(new_balance, 500.0)
        self.assertEqual(len(account.transaction_log), 2)
        self.assertEqual(account.transaction_log[-1].kind, TransactionKind.WITHDRAWAL)

        # Test invalid withdrawals
        with self.assertRaises(ValueError):
            self.bank.withdraw(0, -100.0)
        with self.assertRaises(ValueError):
            self.bank.withdraw(0, 0)
        with self.assertRaises(InsufficientFundsError):
            self.bank.withdraw(0, 1000.0)
        with self.assertRaises(AccountNotFoundError):
            self.bank.withdraw(999, 100.0)

    def test_delete_account(self):
        # Test successful deletion
        self.bank.create_account("Charlie", 300.0)
        self.assertTrue(self.bank.delete_account(0))
        with self.assertRaises(AccountNotFoundError):
            self.bank.read_account(0)

        # Test deleting non-existent account
        with self.assertRaises(AccountNotFoundError):
            self.bank.delete_account(999)

    def test_transfer(self):
        # Setup test accounts
        acc1 = self.bank.create_account("Sender", 1000.0)
        acc2 = self.bank.create_account("Receiver", 500.0)

        # Test successful transfer
        balances = self.bank.transfer(0, 1, 300.0)
        self.assertEqual(balances[0], 700.0)
        self.assertEqual(balances[1], 800.0)
        self.assertEqual(acc1.transaction_log[-1].kind, TransactionKind.TRANSFER)
        self.assertEqual(acc2.transaction_log[-1].kind, TransactionKind.TRANSFER)

        # Test invalid transfers
        with self.assertRaises(ValueError):
            self.bank.transfer(0, 0, 100.0)  # Same account
        with self.assertRaises(ValueError):
            self.bank.transfer(0, 1, -100.0)  # Negative amount
        with self.assertRaises(ValueError):
            self.bank.transfer(0, 1, 0)  # Zero amount
        with self.assertRaises(InsufficientFundsError):
            self.bank.transfer(0, 1, 1000.0)  # Insufficient funds
        with self.assertRaises(AccountNotFoundError):
            self.bank.transfer(0, 999, 100.0)  # Non-existent receiver
        with self.assertRaises(AccountNotFoundError):
            self.bank.transfer(999, 0, 100.0)  # Non-existent sender

    def test_concurrent_operations(self):
        # Test concurrent deposits
        account = self.bank.create_account("Test User", 1000.0)
        num_deposits = 100
        deposit_amount = 10.0

        def make_deposit():
            self.bank.deposit(0, deposit_amount)

        threads = [threading.Thread(target=make_deposit) for _ in range(num_deposits)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_balance = self.bank.read_account(0).balance
        expected_balance = 1000.0 + (deposit_amount * num_deposits)
        self.assertEqual(final_balance, expected_balance)

        # Test concurrent transfers
        acc1 = self.bank.create_account("Account1", 1000.0)
        acc2 = self.bank.create_account("Account2", 1000.0)
        num_transfers = 50
        transfer_amount = 10.0

        def make_transfer():
            try:
                self.bank.transfer(1, 2, transfer_amount)
            except (InsufficientFundsError, ValueError):
                pass

        threads = [threading.Thread(target=make_transfer) for _ in range(num_transfers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_balance = self.bank.read_account(1).balance + self.bank.read_account(2).balance
        self.assertEqual(total_balance, 2000.0)  # Total money in system should remain constant

    def test_transaction_log(self):
        # Create account and perform various operations
        account = self.bank.create_account("Test User", 1000.0)

        self.bank.deposit(0, 500.0)
        self.bank.withdraw(0, 200.0)

        # Verify transaction log
        log = account.transaction_log
        self.assertEqual(len(log), 3)
        self.assertEqual(log[0].kind, TransactionKind.CREATION)
        self.assertEqual(log[1].kind, TransactionKind.DEPOSIT)
        self.assertEqual(log[2].kind, TransactionKind.WITHDRAWAL)

        # Verify transaction amounts
        self.assertEqual(log[0].amount, 1000.0)
        self.assertEqual(log[1].amount, 500.0)
        self.assertEqual(log[2].amount, -200.0)

        # Verify balances after each transaction
        self.assertEqual(log[0].balance_after, 1000.0)
        self.assertEqual(log[1].balance_after, 1500.0)
        self.assertEqual(log[2].balance_after, 1300.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
