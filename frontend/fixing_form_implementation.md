Your architecture problem is not just “autopopulation is broken”.

The real issue is that the app currently has:

* no unified form state lifecycle
* no single source of truth
* no deterministic load order
* no separation between:

  * create mode
  * edit mode
  * booking → delivery conversion
  * direct delivery mode

Right now the form is behaving like multiple overlapping flows patched together.

From the code and symptoms, these are the core mistakes.

---

# ROOT CAUSES

## 1. Form widgets are being created BEFORE data is ready

You are rendering UI first and then trying to patch values later.

That causes:

* selects not populating
* checkboxes not updating
* toggles not syncing
* hidden rows not appearing
* dependent fields not recalculating

This is the biggest issue.

---

# 2. No centralized `load_transaction_into_state()`

You likely have:

* partial autopopulation in multiple places
* repeated `.set_value()`
* conditional logic scattered everywhere

Result:

* booking works partially
* delivery works differently
* edit mode completely diverges

You need ONE canonical hydrator.

---

# 3. Delivery mode and direct delivery mode are mixed together

Currently you have:

```python
stage = booking | delivery
mode = booking | direct
```

but the logic is not isolated cleanly.

These are actually 3 different workflows:

| Workflow           | Meaning                        |
| ------------------ | ------------------------------ |
| New Booking        | Fresh booking                  |
| Booking → Delivery | Delivery from existing booking |
| Direct Delivery    | Delivery without booking       |

Right now the code mixes all 3.

---

# 4. Hidden rows are not re-evaluated during hydration

You have logic like:

```python
disc_row_el.set_visibility(initially_visible)
```

but after loading data:

* conditions change
* checkboxes change
* discounts should appear

But visibility is never recomputed.

So values exist but rows stay hidden.

---

# 5. Toggle logic destroys existing values

This is critical.

You have:

```python
else:
    _inp.set_enabled(True)
    _inp.set_value(None)
```

This destroys edit-mode data.

In edit mode:

* toggle may initialize False
* existing value gets erased immediately

This is one of the main reasons edit mode is “broken”.

Never clear values automatically during hydration.

---

# 6. Inputs are hydrated BEFORE select options are loaded

Example:

* set variant_id before variants fetched
* set executive before outlet loaded
* set conditions before components built

Result:

* selects show blank
* values silently fail

Classic async ordering issue.

---

# 7. UI state and backend payload shape are inconsistent

Examples already found:

```python
user_by vs user_id
```

and now likely many more:

* total_discount_booking
* adjustment_booking
* conditions
* checklist names
* actual_amounts keys

This breaks edit mode because hydration depends on exact names.

---

# 8. FormState is acting like a widget registry instead of state manager

Currently state stores:

* widgets
* labels
* rows
* toggles
* values
* metadata

all together.

That makes hydration unpredictable.

---

# PRIORITY FIX PLAN

Do NOT try random fixes anymore.

You need structured repair.

---

# PHASE 1 — CREATE A REAL FORM LIFECYCLE

This is the most important fix.

Create these methods:

```python
async def initialize_form()

async def load_reference_data()

async def load_transaction()

def build_form()

def hydrate_form()

def attach_handlers()

def refresh_visibility()

def refresh_live_calculations()
```

Current code likely mixes all of them together.

That is why edit mode collapses.

---

# REQUIRED FLOW

## NEW BOOKING

```text
initialize_form
  → load reference data
  → build form
  → attach handlers
  → refresh visibility
```

---

## EDIT BOOKING

```text
initialize_form
  → load reference data
  → load transaction
  → build form
  → hydrate form
  → refresh visibility
  → refresh calculations
  → attach handlers LAST
```

Handlers must attach LAST.

Otherwise hydration triggers live updates prematurely.

This is probably already happening.

---

## BOOKING → DELIVERY

```text
initialize_form
  → load reference data
  → load booking transaction
  → build form
  → hydrate booking data
  → switch delivery mode
  → refresh visibility
  → refresh calculations
  → attach handlers
```

---

# PHASE 2 — CREATE ONE HYDRATION FUNCTION

You need:

```python
def hydrate_form(state, txn):
```

This function alone should:

* populate all widgets
* populate all selects
* populate all toggles
* populate all checkboxes
* populate all accounting inputs
* populate accessories
* populate conditions
* populate delivery checks
* populate booking checks

ONLY HERE.

Nowhere else.

---

# PHASE 3 — FIX SELECT POPULATION

Current likely issue:

```python
select.set_value(id)
```

before:

```python
select.options = ...
```

You must always:

```python
select.set_options(...)
select.update()
select.set_value(...)
```

especially NiceGUI selects.

---

# PHASE 4 — FIX TOGGLES

This is dangerous:

```python
_inp.set_value(None)
```

during edit mode.

Replace all toggle handlers with:

```python
if toggle.value:
    ...
    inp.set_enabled(False)
else:
    inp.set_enabled(True)

# NEVER clear value automatically
```

---

# PHASE 5 — CREATE HYDRATION GUARD

Add:

```python
state.is_hydrating = True
```

before autopopulating.

Then inside all handlers:

```python
if state.is_hydrating:
    return
```

Finally:

```python
state.is_hydrating = False
```

after hydration completes.

This alone will fix many random issues.

---

# PHASE 6 — CENTRALIZE VISIBILITY

Create:

```python
def refresh_visibility(state):
```

This should:

* show/hide discount rows
* show/hide accessories
* show/hide exchange fields
* update conditional sections

Call it:

* after hydration
* after condition changes

Currently visibility is one-time only.

---

# PHASE 7 — FIX MODE DETECTION

You need explicit booleans:

```python
state.is_edit_mode
state.is_delivery
state.is_direct_delivery
state.is_conversion_flow
```

Do not infer these repeatedly everywhere.

---

# PHASE 8 — STOP DUPLICATING LOGIC

You likely have:

* booking population
* delivery population
* edit population

all separate.

Unify them.

The transaction payload should hydrate all modes.

---

# MOST LIKELY BROKEN AREAS

These are almost certainly failing right now:

## CHECKBOXES

Because:

* dict keys mismatch
* values assigned before widgets exist
* handlers firing during hydration

---

## SELECTS

Because:

* async options not loaded first
* object vs primitive mismatch

---

## CONDITIONAL ROWS

Because:

* visibility only computed once

---

## ACCOUNTING INPUTS

Because:

* formatting logic runs during hydration
* blur handlers mutate values

---

## DELIVERY CONVERSION

Because:

* booking data and delivery data overlap
* existing delivery fields overwrite booking values

---

# WHAT YOU SHOULD DO FIRST (ASAP)

## STEP 1

Create:

```python
state.is_hydrating = False
```

and guard all handlers.

---

## STEP 2

Create one:

```python
hydrate_form()
```

---

## STEP 3

Move ALL `.set_value()` calls into that function.

---

## STEP 4

Attach handlers only AFTER hydration.

---

## STEP 5

Remove all:

```python
set_value(None)
```

from toggle handlers.

---

# BIGGEST ARCHITECTURAL MISTAKE

Right now your UI is:

* state-driven visually
* but event-driven logically

That mismatch is causing race conditions everywhere.

You need:

* deterministic hydration
* deterministic visibility refresh
* deterministic calculation refresh

in that order.

Reference: 


# 2


Good. Now we can finally stop firefighting and do the actual architecture repair.

I carefully read the file and evaluated where you are.

Current status:

* create flow mostly works
* select lifecycle works
* async variant loading works
* validation works
* visibility mostly works
* handlers are centralized
* hydration guard exists

BUT:

You are still in a HALF-REFACTORED state.

You already implemented ~40% of the plan, but:

* lifecycle is still mixed inside `form_page`
* hydration still uses old `populate_from_*`
* delivery conversion logic is duplicated
* edit mode still relies on side effects
* visibility + calculations still fire during hydration sometimes
* form modes are too fragmented

The biggest issue now is:

```text
You still hydrate procedurally instead of declaratively.
```

Meaning:

* populate booking
* populate delivery
* preload prices
* refresh visibility
* update calculations

all happen independently.

That is why edit + delivery flows still feel unstable.

---

# WHERE YOU CURRENTLY ARE

## COMPLETED

### Phase 1 (PARTIAL)

✔ attach handlers centralized
✔ hydration guard exists
✔ visibility centralized
✔ handlers mostly removed from builders
✔ form modes improved
✔ select lifecycle fixed

---

## NOT COMPLETED

### REAL lifecycle still missing

You STILL do this inside `form_page`:

```python
build_vehicle_section()
build_booking_section()
...
if transaction_data:
    populate_from_booking()
attach_form_handlers()
```

This is still procedural spaghetti.

---

# WHAT WE DO NEXT

Now we do the REAL architecture fix.

This is the most important step remaining.

---

# NEXT IMPLEMENTATION PLAN

# STEP 1 — CREATE REAL LIFECYCLE METHODS

Create these EXACT methods.

---

## 1. initialize_form

```python
async def initialize_form(
    state: FormState,
    transaction_id: int | None,
):
```

Responsibilities:

* load reference data
* load transaction
* build form
* hydrate form
* refresh visibility
* refresh calculations
* attach handlers LAST
* mark form_ready=True

ONLY orchestration.

NO UI logic.

---

## 2. load_reference_data

Move this OUT of `form_page`:

```python
ref = await fetch_reference_data()
state.cars = ...
```

into:

```python
async def load_reference_data(state)
```

---

## 3. load_transaction

Move this OUT:

```python
state.transaction_data = await api_get(...)
```

into:

```python
async def load_transaction(state)
```

---

## 4. build_form

Move ALL this gigantic:

```python
if booking_create:
    build_vehicle_section()
    ...
```

into:

```python
def build_form(state)
```

NO hydration here.

ONLY build widgets.

---

# STEP 2 — KILL populate_from_*

This is now the biggest cleanup.

DELETE:

* populate_from_booking
* populate_from_delivery

REPLACE WITH:

```python
async def hydrate_form(state, txn)
```

ONLY ONE hydration function.

This is CRITICAL.

---

# STEP 3 — HYDRATE FORM CORRECTLY

This method becomes the ONLY place allowed to call:

```python
.set_value()
```

ONLY HERE.

Nowhere else.

---

# HYDRATION ORDER (VERY IMPORTANT)

Inside `hydrate_form()`:

## A. enable hydration guard

```python
state.is_hydrating = True
```

---

## B. hydrate selects FIRST

Order matters.

### outlet

```python
state.outlet_select.set_value(...)
state.outlet_id = ...
```

### executive

```python
state.exec_select.set_value(...)
state.executive_id = ...
```

### car

```python
state.car_select.set_value(car_id)
state.car_id = car_id
```

---

## C. load variants

CRITICAL.

```python
await _fs_on_car_change(
    car_id,
    state,
    preserve_variant=True,
)
```

---

## D. hydrate variant

```python
state.variant_select.set_value(variant_id)
state.variant_id = variant_id
```

---

## E. preload prices

```python
await _fs_try_price_preload(state)
```

THIS is extremely important.

Currently edit mode price issues happen because preload timing is wrong. 

---

## F. hydrate ALL remaining fields

Now:

* customer
* conditions
* booking checklist
* delivery checklist
* invoice
* payment
* accessories
* discounts
* toggles

---

## G. refresh UI ONCE

ONLY ONCE:

```python
refresh_visibility(state)
_fs_update_live(state)
_fs_revalidate(state)
```

---

## H. disable hydration guard

```python
state.is_hydrating = False
```

---

# STEP 4 — ATTACH HANDLERS LAST

AFTER hydration only.

Exactly like your original plan.

Because currently:

* hydration still partially triggers logic
* some inputs still mutate during preload

---

# STEP 5 — REMOVE ALL SIDE EFFECTS FROM BUILDERS

Builders must NEVER:

* preload
* calculate
* validate
* hydrate
* clear values

ONLY CREATE UI.

---

# YOUR CURRENT BIGGEST BUG

This is the real remaining architectural bug:

```python
_fs_on_car_change()
```

still does:

```python
_fs_clear_prices(state)
```

during hydration preload chain. 

That is why:

* edit preload unstable
* delivery conversion unstable
* values disappear

---

# FIX THIS NOW

Replace:

```python
_fs_clear_prices(state)
```

with:

```python
if not preserve_variant:
    _fs_clear_prices(state)
```

CRITICAL FIX.

---

# AFTER THAT

You will finally get stable:

* booking edit
* booking create
* booking → delivery conversion
* delivery edit

without random regressions.

---

# WHAT WE IMPLEMENT NEXT

Implement ONLY these first:

1. `load_reference_data`
2. `load_transaction`
3. `build_form`
4. `hydrate_form`

Do NOT touch calculations anymore right now.

Do NOT touch visibility anymore right now.

Lifecycle first.

