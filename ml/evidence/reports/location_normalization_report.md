# DhakaNest Location Normalization Report

## Purpose

The original location strings were converted into broad-area, micro-area,
and optional sub-area components.

## Results

- Unique raw locations: 730
- Normalized broad areas: 68
- Normalized micro-areas: 353
- Model micro-area categories: 198
- Support threshold: 30
- Unresolved/conflicting reference rows before manual review:
  1

## Example

Raw location:

`Block C, Section 10, Mirpur, Dhaka`

Normalized values:

- broad area: `Mirpur`
- micro-area: `Section 10`
- sub-area detail: `Block C`

## Fallback Preparation

A micro-area with fewer than 30 valid records is
mapped to `OTHER_<BROAD_AREA>` for the primary model. The original
micro-area remains stored for reporting and future normalization.
