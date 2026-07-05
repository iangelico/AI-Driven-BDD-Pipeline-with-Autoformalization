Feature: Checking Account Cash Withdrawals

  Scenario: Successful cash withdrawal
    Given the account balance is $1000
    When the customer withdraws $200
    Then the withdrawal should succeed
    And the balance should be 800 dollars

  Scenario: Biometric verification step test
    When the user scans a biometric token
    Then the withdrawal should succeed