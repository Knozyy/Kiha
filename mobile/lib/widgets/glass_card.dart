import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:kiha_mobile/theme/kiha_theme.dart';

/// Reusable glassmorphism card widget.
/// Adapts to dark/light theme automatically.
class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(24),
    this.borderRadius = 16,
    this.margin = EdgeInsets.zero,
  });

  final Widget child;
  final EdgeInsets padding;
  final double borderRadius;
  final EdgeInsets margin;

  @override
  Widget build(BuildContext context) {
    final bool isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      margin: margin,
      decoration: BoxDecoration(
        color: isDark ? KihaTheme.darkGlass : KihaTheme.lightGlass,
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(
          color: isDark ? KihaTheme.darkGlassBorder : KihaTheme.lightGlassBorder,
        ),
        boxShadow: isDark
            ? null
            : [
                BoxShadow(
                  color: Colors.black.withOpacity(0.04),
                  blurRadius: 24,
                  offset: const Offset(0, 4),
                ),
              ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(borderRadius),
        child: BackdropFilter(
          filter: ImageFilter.blur(
            sigmaX: isDark ? 12 : 20,
            sigmaY: isDark ? 12 : 20,
          ),
          child: Padding(
            padding: padding,
            child: child,
          ),
        ),
      ),
    );
  }
}
