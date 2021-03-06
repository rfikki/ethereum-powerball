from eth_tools import Contract, address
from nose.tools import assert_equal
from pyethereum import tester as t

INITIALIZE = 0
SET_CONFIGURATION = 1
BUY_TICKET = 2
GET_TICKET_OWNER = 3
GET_TICKET_NUMBERS = 4
TRANSFER_TICKET = 5
CHECK_WINNERS = 6
CLAIM_WINNINGS = 7
GET_BALANCE = 8
SET_PAYOUTS = 9
WITHDRAW = 10
START_LOTTO = 11

class TestLotto:
    def setup(self):
        self.state = t.state()
        self.contract = Contract("contracts/lotto.se", self.state)
        self.contract.call(INITIALIZE)
        self.state.mine(1)

    def test_buying_ticket(self):
        numbers = [1, 3, 4, 5, 9, 35]
        self.contract.call(START_LOTTO)
        ticket_id = self.contract.call(BUY_TICKET, numbers)[0]

        assert_equal(address(self.contract.call(GET_TICKET_OWNER, [ticket_id])[0]), t.a0)
        assert_equal(self.contract.call(GET_TICKET_NUMBERS, [ticket_id]), numbers)

        new_numbers = [1, 5, 7, 8, 10, 35]
        new_ticket_id = self.contract.call(BUY_TICKET, new_numbers)[0]

        assert_equal(address(self.contract.call(GET_TICKET_OWNER, [new_ticket_id])[0]), t.a0)
        assert_equal(self.contract.call(GET_TICKET_NUMBERS, [new_ticket_id]), new_numbers)

    def test_cannot_buy_invalid_ticket(self):
        numbers = [1, 1, 2, 3, 5, 8]
        self.contract.call(START_LOTTO)
        assert_equal(self.contract.call(BUY_TICKET, numbers), [-3])

    def test_lotto_closes_after_specified_block(self):
        self.contract.call(SET_CONFIGURATION, [0, 0, 4])
        self.contract.call(START_LOTTO)
        self.state.mine(5)
        numbers = [1, 3, 4, 5, 9, 35]

        assert_equal(self.contract.call(BUY_TICKET, numbers), [-2])

    def test_ticket_prices(self):
        numbers = [1, 3, 4, 5, 9, 35]
        self.contract.call(SET_CONFIGURATION, [1])
        self.contract.call(START_LOTTO)

        assert_equal(self.contract.call(BUY_TICKET, numbers, ether=0), [-1])
        assert_equal(self.contract.call(BUY_TICKET, numbers, ether=1), [0])


    def test_transfering_ticket(self):
        numbers = [1, 3, 4, 5, 9, 35]
        self.contract.call(START_LOTTO)
        ticket_id = self.contract.call(BUY_TICKET, numbers)[0]

        self.contract.call(TRANSFER_TICKET, [ticket_id, t.a1])

        assert_equal(address(self.contract.call(GET_TICKET_OWNER, [ticket_id])[0]), t.a1)

    def test_check_winning_numbers(self):
        rng = Contract("contracts/fake_rng.se", self.state)
        self.contract.call(SET_CONFIGURATION, [0, rng.contract, 4])
        self.contract.call(START_LOTTO)
        assert_equal(self.contract.call(CHECK_WINNERS), [-1])

        self.state.mine(5)
        assert_equal(self.contract.call(CHECK_WINNERS), [1,2,5,6,7,1])

    def test_claim_winnings(self):
        rng = Contract("contracts/fake_rng.se", self.state)
        self.contract.call(SET_CONFIGURATION, [0, rng.contract, 4, 4], ether = 1000)
        self.contract.call(SET_PAYOUTS, [0, 0, 0, 0, 1000, 101, 0, 0, 0, 0, 0, 0])
        self.contract.call(START_LOTTO)
        numbers = [1, 2, 3, 4, 5, 35]
        ticket_id = self.contract.call(BUY_TICKET, numbers)[0]

        self.state.mine(5)
        assert_equal(self.contract.call(CHECK_WINNERS), [1,2,5,6,7,1])

        assert_equal(self.contract.call(CLAIM_WINNINGS, [ticket_id]), [101])

    def test_cannot_overwrite_winning_numbers(self):
        self.contract.call(SET_CONFIGURATION, [0, 0, 4, 4], ether = 1000)
        self.contract.call(SET_PAYOUTS, [0, 0, 0, 0, 1000, 101, 0, 0, 0, 0, 0, 0])
        self.contract.call(START_LOTTO)

        self.state.mine(5)

        winning_numbers = self.contract.call(CHECK_WINNERS)
        assert_equal(len(winning_numbers), 6)

        self.state.mine(1)

        assert_equal(self.contract.call(CHECK_WINNERS), [-2])

    def test_cannot_claim_winnings_after_deadline(self):
        rng = Contract("contracts/fake_rng.se", self.state)
        self.contract.call(SET_CONFIGURATION, [0, rng.contract, 2, 2], ether = 1000)
        self.contract.call(SET_PAYOUTS, [0, 0, 0, 0, 1000, 101, 0, 0, 0, 0, 0, 0])
        self.contract.call(START_LOTTO)
        numbers = [1, 2, 3, 4, 5, 35]
        ticket_id = self.contract.call(BUY_TICKET, numbers)[0]

        self.state.mine(5)

        assert_equal(self.contract.call(CHECK_WINNERS), [1,2,5,6,7,1])

        assert_equal(self.contract.call(CLAIM_WINNINGS, [ticket_id]), [-1])

    def test_cannot_double_claim_winnings(self):
        rng = Contract("contracts/fake_rng.se", self.state)
        self.contract.call(SET_CONFIGURATION, [0, rng.contract, 4, 4], ether = 1000)
        self.contract.call(SET_PAYOUTS, [0, 0, 0, 0, 1000, 101, 0, 0, 0, 0, 0, 0])
        self.contract.call(START_LOTTO)
        numbers = [1, 2, 3, 4, 5, 35]
        ticket_id = self.contract.call(BUY_TICKET, numbers)[0]

        self.state.mine(5)
        assert_equal(self.contract.call(CHECK_WINNERS), [1,2,5,6,7,1])

        assert_equal(self.contract.call(CLAIM_WINNINGS, [ticket_id]), [101])
        assert_equal(self.contract.call(CLAIM_WINNINGS, [ticket_id]), [-2])

    def test_multiple_winners_split_jackpot(self):
        rng = Contract("contracts/fake_rng.se", self.state)
        self.contract.call(SET_CONFIGURATION, [0, rng.contract, 4, 4], ether = 1000)
        self.contract.call(SET_PAYOUTS, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1000, 0])
        self.contract.call(START_LOTTO)
        numbers = [1, 2, 5, 6, 7, 1]
        ticket_id = self.contract.call(BUY_TICKET, numbers)[0]
        second_ticket_id = self.contract.call(BUY_TICKET, numbers)[0]

        self.state.mine(5)
        assert_equal(self.contract.call(CHECK_WINNERS), [1,2,5,6,7,1])
        assert_equal(self.contract.call(CLAIM_WINNINGS, [ticket_id]), [500])

    def test_withdrawal_is_only_possible_after_lotto_deadline(self):
        self.contract.call(SET_CONFIGURATION, [0, 0, 2, 2], ether = 1000)
        self.contract.call(START_LOTTO)

        assert_equal(self.contract.call(WITHDRAW, [500]), [-1])

        self.state.mine(5)

        assert_equal(self.contract.call(WITHDRAW, [500]), [500])

    def test_start_new_lotto(self):
        rng = Contract("contracts/fake_rng.se", self.state)
        self.contract.call(SET_CONFIGURATION, [0, rng.contract, 2, 2], ether = 1000)
        self.contract.call(SET_PAYOUTS, [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1000, 0])
        self.contract.call(START_LOTTO)
        assert_equal(self.contract.call(START_LOTTO), [-1])

        self.state.mine(5)

        assert_equal(self.contract.call(START_LOTTO), [1])
        numbers = [1, 2, 5, 6, 7, 1]
        ticket_id = self.contract.call(BUY_TICKET, numbers)[0]
        assert_equal(ticket_id, 0)

        self.state.mine(3)
        assert_equal(self.contract.call(CHECK_WINNERS), [1,2,5,6,7,1])
        assert_equal(self.contract.call(CLAIM_WINNINGS, [ticket_id]), [1000])
