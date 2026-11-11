# src/context

React "context" shares data with every screen without passing it through each component.

Empty in Slice 1.2. Slice 1.5 adds `AuthContext.jsx`, which holds the logged-in user,
their role and their token, plus `login()` / `logout()` helpers.
