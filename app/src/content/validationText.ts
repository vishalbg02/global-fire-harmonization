/** Texts of the validation overview (T-089). They restate how the page reads the stored file; no result is described here. */

export const OVERVIEW_NOTE =
  'One line per test family, with the status the results file holds. Failures and inconclusive results are shown as strongly as passes, and each line opens the detail of its entry.'

export const FAMILY_RULE_TEXT =
  'A family takes the status of its own family-level entry when the file has one. Otherwise, except for D1 (below), it takes the worst status of its entries (fail, then inconclusive, then not run, then pass); the entry counts beside it show what is inside. One family, D1, has no family-level entry: its official entry is the pooled share over all fire regions (the decision of the Lead on PR #56), and its per-region and night entries are listed as their own failures right under it.'
