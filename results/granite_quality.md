# Granite quality check (M5 evidence)

- Distinct prompts: 30 (cache bypassed: each one is a fresh generation)
- Passed the output and quality guards: 28 (93%); the rest fall back to the human-written template. Gate: ≥ 80%
- Generation time: p50 10.4 s, p95 11.2 s, max 11.2 s

## Every output

### NEW_RECIPIENT, RISKY_TRANSFER_TYPE, LARGE_AMOUNT  (PASS, 11.2 s)
- Model said: This is a very big payment, and it's late at night. Please stop for just one moment to call your bank on the number you have in hand.
- Stored (explanation + fixed action): This is a very big payment, and it's late at night. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: The receiving account is new and has not received transfers before. This transfer method is commonly targeted by urgent payment scams. The requested amount is unusually large compared to your normal activity. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE, NEW_RECIPIENT, LARGE_AMOUNT  (PASS, 10.9 s)
- Model said: This is a very big payment, and it uses up most of your money. Please wait for the bank to verify this transfer by calling on their number.
- Stored (explanation + fixed action): This is a very big payment, and it uses up most of your money. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. The receiving account is new and has not received transfers before. The requested amount is unusually large compared to your normal activity. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### ACCOUNT_DRAIN, RISKY_TRANSFER_TYPE, OTHER_PATTERN  (PASS, 10.4 s)
- Model said: This transfer would drain your account, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This transfer would drain your account, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment would completely drain your remaining balance. This transfer method is commonly targeted by urgent payment scams. Unusual transaction indicators were detected for this transfer. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE, NEW_RECIPIENT, UNUSUAL_TIME  (PASS, 11.2 s)
- Model said: This is a very big payment, and it's late at night. Please stop for just one moment to call your bank on the number you have in front of.
- Stored (explanation + fixed action): This is a very big payment, and it's late at night. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. The receiving account is new and has not received transfers before. This payment is occurring at an unusual hour. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE  (PASS, 9.1 s)
- Model said: This payment would use up most of your money, and scammers often ask for payments like this. Please wait.
- Stored (explanation + fixed action): This payment would use up most of your money, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### ACCOUNT_DRAIN, MULE_ACCOUNT_PATTERN  (PASS, 9.9 s)
- Model said: This payment would drain your account, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would drain your account, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment would completely drain your remaining balance. The destination account matches characteristics of an unauthorized relay account. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE, ACCOUNT_DRAIN, MULE_ACCOUNT_PATTERN  (PASS, 10.3 s)
- Model said: This payment would drain your account, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would drain your account, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. This payment would completely drain your remaining balance. The destination account matches characteristics of an unauthorized relay account. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE, MULE_ACCOUNT_PATTERN, UNUSUAL_TIME  (PASS, 11.2 s)
- Model said: This is a very big payment, and it's late at night. Please stop for just one moment to call your bank on the number you have in hand.
- Stored (explanation + fixed action): This is a very big payment, and it's late at night. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. The destination account matches characteristics of an unauthorized relay account. This payment is occurring at an unusual hour. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### ACCOUNT_DRAIN, NEW_RECIPIENT, RISKY_TRANSFER_TYPE  (PASS, 10.6 s)
- Model said: This payment would drain your account completely, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would drain your account completely, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment would completely drain your remaining balance. The receiving account is new and has not received transfers before. This transfer method is commonly targeted by urgent payment scams. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### LARGE_AMOUNT, UNUSUAL_TIME, OTHER_PATTERN  (PASS, 10.9 s)
- Model said: This is a very big payment, and it's late at night. Please stop for just one moment to call your bank on the number you have in hand.
- Stored (explanation + fixed action): This is a very big payment, and it's late at night. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: The requested amount is unusually large compared to your normal activity. This payment is occurring at an unusual hour. Unusual transaction indicators were detected for this transfer. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE, NEW_RECIPIENT, RISKY_TRANSFER_TYPE  (PASS, 11.1 s)
- Model said: This payment would use up most of your money, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would use up most of your money, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. The receiving account is new and has not received transfers before. This transfer method is commonly targeted by urgent payment scams. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### ACCOUNT_DRAIN, NEW_RECIPIENT, LARGE_AMOUNT  (PASS, 10.6 s)
- Model said: This is a very big payment, and it would drain your account. Please wait for the bank to verify this transfer by calling on their number.
- Stored (explanation + fixed action): This is a very big payment, and it would drain your account. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment would completely drain your remaining balance. The receiving account is new and has not received transfers before. The requested amount is unusually large compared to your normal activity. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE, RISKY_TRANSFER_TYPE, MULE_ACCOUNT_PATTERN  (PASS, 10.6 s)
- Model said: This payment would use up most of your money, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would use up most of your money, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. This transfer method is commonly targeted by urgent payment scams. The destination account matches characteristics of an unauthorized relay account. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### ACCOUNT_DRAIN  (PASS, 9.7 s)
- Model said: This payment would completely drain your money, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would completely drain your money, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment would completely drain your remaining balance. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### NEW_RECIPIENT, RISKY_TRANSFER_TYPE  (FAIL: Output contains 'you have not received', 10.4 s)
- Model said: This is a new account, and you have not received any transfers before. Please wait for your bank to verify this transfer by calling on the number.
- Stored (explanation + fixed action): This is a new account, and you have not received any transfers before. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: The receiving account is new and has not received transfers before. This transfer method is commonly targeted by urgent payment scams. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### LARGE_AMOUNT, UNUSUAL_TIME  (PASS, 10.4 s)
- Model said: This is a very big payment, and it's late at night. Please stop for just one moment to call your bank on the number they give you.
- Stored (explanation + fixed action): This is a very big payment, and it's late at night. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: The requested amount is unusually large compared to your normal activity. This payment is occurring at an unusual hour. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE, OTHER_PATTERN  (PASS, 10.5 s)
- Model said: This is a very big payment, and it uses up most of your money. Please wait for the bank to verify this transfer by calling on their number.
- Stored (explanation + fixed action): This is a very big payment, and it uses up most of your money. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. Unusual transaction indicators were detected for this transfer. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE, RISKY_TRANSFER_TYPE  (PASS, 9.5 s)
- Model said: This payment would use up most of your money, and scammers often ask for payments like this. Please wait.
- Stored (explanation + fixed action): This payment would use up most of your money, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. This transfer method is commonly targeted by urgent payment scams. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### RISKY_TRANSFER_TYPE, LARGE_AMOUNT, UNUSUAL_TIME  (PASS, 11.0 s)
- Model said: This is a very big payment, and it's late at night. Please stop for just one moment to call your bank on the number they give you.
- Stored (explanation + fixed action): This is a very big payment, and it's late at night. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This transfer method is commonly targeted by urgent payment scams. The requested amount is unusually large compared to your normal activity. This payment is occurring at an unusual hour. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### ACCOUNT_DRAIN, RISKY_TRANSFER_TYPE  (PASS, 10.0 s)
- Model said: This payment would completely drain your money, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would completely drain your money, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment would completely drain your remaining balance. This transfer method is commonly targeted by urgent payment scams. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE, ACCOUNT_DRAIN, LARGE_AMOUNT  (PASS, 10.6 s)
- Model said: This payment would use up most of your money, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would use up most of your money, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. This payment would completely drain your remaining balance. The requested amount is unusually large compared to your normal activity. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### ACCOUNT_DRAIN, NEW_RECIPIENT, MULE_ACCOUNT_PATTERN  (PASS, 10.2 s)
- Model said: This payment would drain your account, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would drain your account, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment would completely drain your remaining balance. The receiving account is new and has not received transfers before. The destination account matches characteristics of an unauthorized relay account. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### ACCOUNT_DRAIN, RISKY_TRANSFER_TYPE, MULE_ACCOUNT_PATTERN  (PASS, 10.2 s)
- Model said: This transfer would drain your account, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This transfer would drain your account, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment would completely drain your remaining balance. This transfer method is commonly targeted by urgent payment scams. The destination account matches characteristics of an unauthorized relay account. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### ACCOUNT_DRAIN, RISKY_TRANSFER_TYPE, LARGE_AMOUNT  (PASS, 10.2 s)
- Model said: This payment would drain your money, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would drain your money, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment would completely drain your remaining balance. This transfer method is commonly targeted by urgent payment scams. The requested amount is unusually large compared to your normal activity. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### NEW_RECIPIENT, UNUSUAL_TIME  (PASS, 10.5 s)
- Model said: This is a very big payment, and it's late at night. Please stop for just one moment to call your bank on the number you have in front of.
- Stored (explanation + fixed action): This is a very big payment, and it's late at night. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: The receiving account is new and has not received transfers before. This payment is occurring at an unusual hour. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### NEW_RECIPIENT, MULE_ACCOUNT_PATTERN  (PASS, 9.6 s)
- Model said: This is a new account, and it has not received transfers before. The destination bank matches characteristics of an unauthorized relay.
- Stored (explanation + fixed action): This is a new account, and it has not received transfers before. The destination bank matches characteristics of an unauthorized relay. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: The receiving account is new and has not received transfers before. The destination account matches characteristics of an unauthorized relay account. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### LARGE_AMOUNT  (PASS, 10.2 s)
- Model said: This is a very big payment, and it's late at night. Please stop for just one moment to call your bank on the number they give you.
- Stored (explanation + fixed action): This is a very big payment, and it's late at night. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: The requested amount is unusually large compared to your normal activity. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### NEW_RECIPIENT, OTHER_PATTERN  (FAIL: Output contains 'you have not received', 10.4 s)
- Model said: This is a new account, and you have not received any transfers before. Please call your bank on the number they gave to receive this transfer.
- Stored (explanation + fixed action): This is a new account, and you have not received any transfers before. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: The receiving account is new and has not received transfers before. Unusual transaction indicators were detected for this transfer. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### ACCOUNT_DRAIN, NEW_RECIPIENT, UNUSUAL_TIME  (PASS, 10.4 s)
- Model said: This payment would drain your account completely, and scammers often ask for payments like this. Please wait to call the bank on their number.
- Stored (explanation + fixed action): This payment would drain your account completely, and scammers often ask for payments like this. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment would completely drain your remaining balance. The receiving account is new and has not received transfers before. This payment is occurring at an unusual hour. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.

### AMOUNT_HIGH_VS_BALANCE, UNUSUAL_TIME, OTHER_PATTERN  (PASS, 10.9 s)
- Model said: This is a very big payment, and it's late at night. Please stop for just one moment to call your bank on the number you have in hand.
- Stored (explanation + fixed action): This is a very big payment, and it's late at night. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
- Template: This payment uses most of the funds in your account. This payment is occurring at an unusual hour. Unusual transaction indicators were detected for this transfer. Please pause and verify this transfer by calling your bank on the official number on your card before proceeding.
