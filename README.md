# Deeside & Flintshire Fuel Prices

Interactive fuel price map and comparison tool for the Deeside, Flintshire and Chester area. Built for [Deeside.com](https://deeside.com) as part of the Connected Deeside Newsroom.

## Data Source

Designed to connect to the [GOV.UK Fuel Finder Public API](https://www.gov.uk/guidance/access-the-latest-fuel-prices-and-forecourt-data-via-api-or-email). Currently uses sample data based on local station prices. Colour grading is benchmarked against the UK national average (DESNZ weekly road fuel prices).

## Hosting

Deployed via Netlify. Embedded on Deeside.com via iframe.

## Colour Grading

- 🟢 Green = below UK national average
- 🟡 Amber = up to 5p above national average  
- 🔴 Red = more than 5p above national average

National averages update weekly from DESNZ data.
