# Limitations and Future Work

## Current Limitations

- Public OSRM gives traffic-free estimates and has no availability guarantee.
- The controlled benchmark is small: 8 profiles and 12 seeded listings.
- Its relevance judgments are manually assigned development ground truth.
- Larger human-labeled real-user studies are needed before generalizing quality.
- Some development listings use placeholder images.
- Household size is descriptive only.
- Browser JWT storage is suitable for this local demonstration, not a public
  hardened deployment.
- The project is designed for local academic demonstration, not hosted operation.

## Future Work

- Evaluate with a larger Dhaka inventory and real tenant feedback.
- Improve landlord image coverage and listing-data quality.
- Integrate a traffic-aware routing provider when live traffic is required.
- Learn preference signals from explicit user feedback.
- Harden token storage and shared infrastructure if public hosting is later needed.
- Consider deployment only if it becomes a future requirement.
