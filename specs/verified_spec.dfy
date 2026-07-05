class Account {
  var balance: int
  var daily_limit: int
  constructor(initialBalance: int)
    requires initialBalance >= 0
    ensures balance == initialBalance
  {
    balance := initialBalance;
    daily_limit := 500;
  }
  method withdraw(amount: int) returns (success: bool)
    requires amount > 0
    requires balance >= amount
    ensures balance == old(balance) - amount
    modifies this
  {
    balance := balance - amount;
    return true;
  }
}