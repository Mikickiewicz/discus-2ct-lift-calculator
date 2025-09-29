# Stall Model Research

## Real Airfoil Stall Characteristics

### Typical CL vs AoA curve should have:

1. **Linear region** (0° to ~10°): CL = CL0 + slope * AoA
   - Slope ≈ 2π per radian (thin airfoil theory)
   - Modified by finite wing effects: slope_3D = slope_2D / (1 + slope_2D/(π*AR*e))

2. **Non-linear region** (10° to stall): Gradual curve flattening
   - CL increases but at decreasing rate
   - NOT a sharp corner - smooth transition
   - Approaches CL_max asymptotically

3. **Stall point** (typically 14-16° for glider airfoils):
   - Maximum CL achieved
   - Sharp drop immediately after this point

4. **Post-stall** (beyond stall AoA):
   - Sharp initial drop (20-30% loss in first 2-3°)
   - Then more gradual decay
   - Eventually levels off at ~40-50% of CL_max

### Mathematical models used in practice:

1. **Viterna-Corrigan model** (for post-stall)
2. **Spera model** (smooth transition)  
3. **Polynomial fits** for specific airfoils

## Common mistakes in current model:
- Too complex transition logic
- Buffeting effects are artificial 
- No smooth approach to CL_max before stall
- Post-stall behavior unrealistic

## Solution:
Use empirical polynomial or exponential models based on real wind tunnel data patterns.