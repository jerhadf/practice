import unittest
import threading
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

class TestBank(unittest.TestCase):
    def setUp(self):
        self.bank = Bank()

    def test_create_account(self):
        account = self.bank.create_account("John Doe", 1000.0)
        self.assertEqual(account.owner, "John Doe")
        self.assertEqual(account.balance, 1000.0)

    def test_create_account_invalid_owner(self):
        with self.assertRaises(ValueError):
            self.bank.create_account("", 1000.0)

    def test_create_account_negative_balance(self):
        with self.assertRaises(ValueError):
            self.bank.create_account("John Doe", -100.0)

    def test_read_account(self):
        account = self.bank.create_account("Jane Doe", 500.0)
        account_id = 0  # first account created will have ID 0
        read_account = self.bank.read_account(account_id)
        self.assertEqual(read_account.owner, "Jane Doe")
        self.assertEqual(read_account.balance, 500.0)

    def test_read_nonexistent_account(self):
        with self.assertRaises(KeyError):
            self.bank.read_account(999)

    def test_update_balance(self):
        account = self.bank.create_account("Bob Smith", 1000.0)
        account_id = 0
        new_balance = self.bank.update_balance(account_id, 500.0)
        self.assertEqual(new_balance, 1500.0)
        self.assertEqual(self.bank.read_account(account_id).balance, 1500.0)

    def test_update_balance_insufficient_funds(self):
        account = self.bank.create_account("Alice Brown", 100.0)
        account_id = 0
        with self.assertRaises(ValueError):
            self.bank.update_balance(account_id, -200.0)

    def test_delete_account(self):
        account = self.bank.create_account("Charlie Wilson", 300.0)
        account_id = 0
        self.assertTrue(self.bank.delete_account(account_id))
        with self.assertRaises(KeyError):
            self.bank.read_account(account_id)

    def test_delete_nonexistent_account(self):
        with self.assertRaises(ValueError):
            self.bank.delete_account(999)

    def test_read_all_accounts(self):
        self.bank.create_account("User1", 100.0)
        self.bank.create_account("User2", 200.0)
        accounts = self.bank.read_all_accounts()
        self.assertEqual(len(accounts), 2)
        self.assertEqual(accounts[0].owner, "User1")
        self.assertEqual(accounts[1].owner, "User2")

    def test_concurrent_account_creation(self):
        num_accounts = 100
        def create_account(i):
            return self.bank.create_account(f"User{i}", 100.0)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_account, i) for i in range(num_accounts)]
            accounts = [f.result() for f in as_completed(futures)]

        self.assertEqual(len(self.bank.read_all_accounts()), num_accounts)
        account_ids = list(self.bank.read_all_accounts().keys())
        self.assertEqual(len(set(account_ids)), num_accounts)

    def test_concurrent_balance_updates(self):
        account = self.bank.create_account("TestUser", 1000.0)
        account_id = 0
        num_updates = 100
        update_amount = 10.0

        def update_balance():
            self.bank.update_balance(account_id, update_amount)

        threads = [threading.Thread(target=update_balance) for _ in range(num_updates)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_balance = self.bank.read_account(account_id).balance
        expected_balance = 1000.0 + (update_amount * num_updates)
        self.assertEqual(final_balance, expected_balance)

    def test_concurrent_reads_and_writes(self):
        account = self.bank.create_account("TestUser", 1000.0)
        account_id = 0
        num_operations = 100
        results = []

        def random_operation():
            op = random.choice(['read', 'write'])
            if op == 'read':
                return self.bank.read_account(account_id).balance
            else:
                return self.bank.update_balance(account_id, 10.0)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(random_operation) for _ in range(num_operations)]
            results = [f.result() for f in as_completed(futures)]

        self.assertTrue(all(isinstance(r, (float)) for r in results))
        final_balance = self.bank.read_account(account_id).balance
        self.assertGreaterEqual(final_balance, 1000.0)

    def test_concurrent_account_deletion(self):
        num_accounts = 10
        accounts = [self.bank.create_account(f"User{i}", 100.0) for i in range(num_accounts)]

        def delete_and_create(account_id):
            try:
                self.bank.delete_account(account_id)
                time.sleep(0.01)  # simulate some work
                self.bank.create_account(f"NewUser{account_id}", 100.0)
            except ValueError:
                pass  # account might have been already deleted

        threads = [threading.Thread(target=delete_and_create, args=(i,))
                  for i in range(num_accounts)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_accounts = self.bank.read_all_accounts()
        self.assertEqual(len(final_accounts), num_accounts)

    def test_negative_balance_prevention(self):
        account = self.bank.create_account("TestUser", 100.0)
        account_id = 0
        num_withdrawals = 20

        def try_withdraw():
            try:
                self.bank.update_balance(account_id, -10.0)
            except ValueError:
                pass

        threads = [threading.Thread(target=try_withdraw) for _ in range(num_withdrawals)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final_balance = self.bank.read_account(account_id).balance
        self.assertGreaterEqual(final_balance, 0)

    def test_concurrent_mixed_operations(self):
        initial_accounts = 5
        for i in range(initial_accounts):
            self.bank.create_account(f"User{i}", 1000.0)

        def random_bank_operation():
            op = random.choice(['create', 'read', 'update', 'delete'])
            try:
                if op == 'create':
                    return self.bank.create_account(f"User{random.randint(1000,9999)}", 100.0)
                elif op == 'read':
                    account_id = random.randint(0, initial_accounts-1)
                    return self.bank.read_account(account_id)
                elif op == 'update':
                    account_id = random.randint(0, initial_accounts-1)
                    amount = random.uniform(-50, 50)
                    return self.bank.update_balance(account_id, amount)
                else:  # delete
                    account_id = random.randint(0, initial_accounts-1)
                    return self.bank.delete_account(account_id)
            except (ValueError, KeyError):
                return None

        num_operations = 100
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(random_bank_operation) for _ in range(num_operations)]
            _ = [f.result() for f in as_completed(futures)]

        # verify system is still in valid state
        accounts = self.bank.read_all_accounts()
        for account in accounts.values():
            self.assertGreaterEqual(account.balance, 0)

# Run tests in notebook
test_suite = unittest.TestLoader().loadTestsFromTestCase(TestBank)
unittest.TextTestRunner(verbosity=2).run(test_suite)