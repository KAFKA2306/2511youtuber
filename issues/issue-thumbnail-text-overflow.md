### **Issue: Thumbnail Text Overflows Due to Unpredictable Wrapping Logic**

**Description**

The current thumbnail generation process suffers from text overflowing its designated boundaries. Despite having configuration parameters like `max_lines` and `max_chars_per_line`, the text rendering is unpredictable, leading to unprofessional-looking thumbnails. The root cause is not a lack of limits, but the complexity and edge cases in the text wrapping algorithm.

**Detailed Analysis**

The text wrapping mechanism in `src/steps/thumbnail.py` is the source of the issue, due to several factors:

1.  **Dual, Competing Constraints:** The wrapping logic simultaneously enforces a pixel-width limit (`max_width`) and a character count limit (`max_chars_per_line`). This makes behavior hard to predict, as the effective constraint changes depending on the specific characters and font used. Developers cannot rely solely on the character count limit.

2.  **Problematic Greedy Wrapping:** The algorithm wraps text greedily, character by character. It does not handle long words gracefully. Critically, if a single character is wider than the maximum allowed width, it is placed on its own line, *guaranteeing* an overflow for that line.

3.  **Uncontrolled Input Length:** The title text, sourced from upstream steps, has no length validation or truncation applied before being passed to the wrapping function. A very long, unbroken string can easily cause the algorithm to produce overflowing lines.

4.  **Complex Configuration Interplay:** The final text layout depends on a sensitive combination of `width`, `height`, `padding`, `font_size`, `font_path`, `max_lines`, and `max_chars_per_line`. The system is fragile, and the impact of changing one value is not always obvious, making `max_chars_per_line` an unreliable safeguard.

**Impact**

This issue degrades the quality of the final video output. Overflowing text on thumbnails looks unprofessional and can make titles unreadable, negatively affecting user experience and click-through rates.

**Suggested Next Steps**

1.  **Investigate and Refactor `_wrap_text_greedy`:** The handling of single characters or words that exceed `max_width` should be improved. Instead of allowing overflow, consider options like truncation with an ellipsis (...) or dynamically reducing the font size until the text fits.
2.  **Add Input Validation:** Before passing text to the rendering module, validate its length. Very long titles or subtitles should be truncated at the source (`_resolve_title`, `_resolve_subtitle`) in a more intelligent way.
3.  **Simplify Configuration:** Explore simplifying the configuration to make it more intuitive. Relying on pixel width with a robust wrapping algorithm might be more reliable than having a separate character limit.
4.  **Improve Documentation:** Document the text wrapping behavior and provide clear guidelines on how to configure the thumbnail generation to avoid overflows.