# CLI Menu Design

## 1. Unauthenticated Menu

```
1. Login
2. Register
3. Exit
```

## 2. Authenticated - No Group Selected (User Level)

```
1. Select Group
2. Create Group
3. More...
4. Exit
```

---

"More..." Submenu - No Group Selected (User Level)

```
1. Settings
2. Logout
3. Back to Top
4. Exit
```

## 3. Authenticated - Group Selected, No Period Selected (Group Level)

```
1. Select Period
2. Create Period
3. More...
4. Exit
```

---

"More..." Submenu - Group Selected, No Period (Group Level)

```
1. Settings
2. Logout
3. Back to Top
4. Exit
```

## 4. Authenticated - Full Context (Group + Period Selected) (Period Level)

```
1. View Transactions
2. View Balances
3. More...
4. Exit
```

---

"More..." Submenu - Full Context (Group + Period) (Period Level)

```
1. Select Transaction
2. Add Transaction
3. View Settlement Plan
4. Settings
5. Logout
6. Back to Top
7. Exit
```

## 5. Authenticated - Transaction Selected (Transaction Level)

```
1. View Details
2. Approve
3. Reject
4. Edit (draft only)
5. Back to Transactions
6. More...
7. Exit
```

---

"More..." Submenu - Transaction Level

```
1. Delete (draft only)
2. Submit (draft only)
3. Settings
4. Logout
5. Back to Top
6. Exit
```

## 6. Transaction Adding Flow (Guided Flow)

**Triggered from:** Period Level "More..." → "Add Transaction"

**Flow Steps:**

1. Select Type → Expense / Deposit / Refund
2. Enter Transaction Description → Optional overall description
3. Select Payer → Choose from group members

**If Expense Type:** 4. Add Expenses → Add one or more expense items:

- For each expense:
  - Enter Amount → Amount in dollars
  - Select Category → Choose category
  - Configure Split → Select split method (Equal/Amount/Percentage/Personal) and configure shares if needed
- After adding expense: "Add Another Expense" / "Done Adding Expenses"

5. Review & Save → Show summary of transaction and all expenses, options: Save as Draft / Submit / Cancel

**If Deposit or Refund Type:** 4. Enter Amount → Amount in dollars 5. Configure Split → Select split method (Equal/Amount/Percentage/Personal) and configure shares if needed 6. Review & Save → Show summary, options: Save as Draft / Submit / Cancel

**Navigation:**

- Each step shows prompt and current value (if editing)
- Can go back to previous step
- For Expense: Can add multiple expenses (loop in step 4), can remove expenses before saving
- For Deposit/Refund: Single amount entry, no categories
- Can cancel at any step (returns to Period Level)
- Final step: Save as Draft / Submit / Cancel

## 7. Settlement Plan Flow (Guided Flow)

**Triggered from:** Period Level "More..." → "View Settlement Plan"

**Flow Steps:**

1. Check Period Status → If period is open, prompt to close it first
2. View Settlement Plan → Display settlement plan (payer, payee, amounts)
3. Apply Prompt → If settlement plan exists, ask "Apply settlement plan? (y/n)" (default: n)
4. If Yes → Apply settlement (close period if needed, then apply settlement plan)
5. If No → Return to menu

**Navigation:**

- Shows settlement plan in table format
- If no settlement needed (all balances zero), shows message and returns
- If period is already settled, shows message and returns
- User can view without applying (say "no")
- User can view and apply in one flow (say "yes")

## 8. Transaction Editing Flow (Guided Flow)

**Triggered from:** Transaction Level → "Edit (draft only)"

**Flow Steps:**

1. Edit Type → Current: [value], change to: [new value]
2. Edit Description → Current: [value], change to: [new value]
3. Edit Payer → Current: [value], change to: [new value]

**If Expense Type:** 4. Manage Expenses → View/edit expenses:

- List all expenses in transaction
- Options: Edit Expense / Add Expense / Remove Expense / Done
- For editing expense:
  - Edit Amount → Current: [value], change to: [new value]
  - Edit Category → Current: [value], change to: [new value]
  - Edit Split → Current: [value], change to: [new value]

5. Review & Save → Show summary of transaction and all expenses, save changes or cancel

**If Deposit or Refund Type:** 4. Edit Amount → Current: [value], change to: [new value] 5. Edit Split → Current: [value], change to: [new value] 6. Review & Save → Show summary, save changes or cancel

**Navigation:**

- Same as Adding flow
- Shows current values at each step
- Can skip unchanged steps (press Enter to keep current value)
- For Expense: Can add/remove/edit expenses in step 4
- For Deposit/Refund: Edit single amount and split
- Can cancel at any step (returns to Transaction Level)
