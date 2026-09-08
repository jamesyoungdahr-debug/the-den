/* @ds-bundle: {"format":4,"namespace":"HoltOSDesignSystem_b5fa35","components":[{"name":"Button","sourcePath":"components/Button/Button.jsx"},{"name":"Lockup","sourcePath":"components/Lockup/Lockup.jsx"},{"name":"MediaTile","sourcePath":"components/MediaTile/MediaTile.jsx"},{"name":"OtterMark","sourcePath":"components/OtterMark/OtterMark.jsx"},{"name":"Panel","sourcePath":"components/Panel/Panel.jsx"},{"name":"PoolMeter","sourcePath":"components/PoolMeter/PoolMeter.jsx"},{"name":"ProgressRow","sourcePath":"components/ProgressRow/ProgressRow.jsx"},{"name":"RingMark","sourcePath":"components/RingMark/RingMark.jsx"},{"name":"SelectRow","sourcePath":"components/SelectRow/SelectRow.jsx"},{"name":"ServiceIcon","sourcePath":"components/ServiceIcon/ServiceIcon.jsx"},{"name":"StatusPill","sourcePath":"components/StatusPill/StatusPill.jsx"}],"sourceHashes":{"components/Button/Button.jsx":"db2b6b9e74ec","components/Lockup/Lockup.jsx":"bf3696325d3d","components/MediaTile/MediaTile.jsx":"a3d218f72588","components/OtterMark/OtterMark.jsx":"8868ccd61120","components/Panel/Panel.jsx":"b8f44d348a61","components/PoolMeter/PoolMeter.jsx":"1691215f3ead","components/ProgressRow/ProgressRow.jsx":"4cc156333db9","components/RingMark/RingMark.jsx":"e68689cf2e55","components/SelectRow/SelectRow.jsx":"6b30e6622378","components/ServiceIcon/ServiceIcon.jsx":"99c84401125c","components/StatusPill/StatusPill.jsx":"b34ffd581f40"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.HoltOSDesignSystem_b5fa35 = window.HoltOSDesignSystem_b5fa35 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/Button/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const SIZES = {
  sm: {
    padding: '8px 14px',
    fontSize: 12
  },
  md: {
    padding: '10px 20px',
    fontSize: 12.5
  },
  lg: {
    padding: '13px 26px',
    fontSize: 15
  }
};
const VARIANTS = {
  primary: {
    background: 'var(--holt-current)',
    color: 'var(--holt-deep)',
    fontWeight: 800,
    borderColor: 'transparent'
  },
  secondary: {
    background: 'transparent',
    color: 'var(--holt-ink-70)',
    fontWeight: 700,
    borderColor: 'var(--holt-hairline-strong)'
  },
  quiet: {
    background: 'transparent',
    color: 'var(--holt-ink-55)',
    fontWeight: 700,
    borderColor: 'transparent'
  },
  onCurrent: {
    background: 'var(--holt-deep)',
    color: 'var(--holt-ink)',
    fontWeight: 800,
    borderColor: 'transparent'
  }
};
function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  style,
  ...rest
}) {
  const s = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    fontFamily: 'var(--holt-font-core)',
    letterSpacing: '-.2px',
    lineHeight: 1,
    borderRadius: 'var(--holt-radius-sm)',
    borderWidth: 1,
    borderStyle: 'solid',
    cursor: disabled ? 'default' : 'pointer',
    opacity: disabled ? .4 : 1,
    transition: 'filter .12s ease, background .12s ease',
    ...SIZES[size],
    ...VARIANTS[variant],
    ...style
  };
  return /*#__PURE__*/React.createElement("button", _extends({
    type: "button",
    style: s,
    disabled: disabled,
    onClick: onClick
  }, rest), children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/Button/Button.jsx", error: String((e && e.message) || e) }); }

// components/MediaTile/MediaTile.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Poster slot. Art is never invented — the striped ground stands in until real art lands. */
function MediaTile({
  title,
  meta,
  width = 86,
  ratio = 1.48,
  tone = 'current',
  art,
  style,
  ...rest
}) {
  const stripe = tone === 'healthy' ? 'rgba(40,224,200,.24)' : 'rgba(177,77,255,.24)';
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      width,
      flex: 'none',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      width: '100%',
      height: width * ratio,
      borderRadius: 6,
      background: 'var(--holt-raised)',
      backgroundImage: art ? undefined : 'repeating-linear-gradient(135deg,' + stripe + ' 0 6px,transparent 6px 13px)',
      display: 'flex',
      alignItems: 'flex-end',
      padding: 8,
      boxSizing: 'border-box',
      overflow: 'hidden'
    }
  }, art ? /*#__PURE__*/React.createElement("img", {
    src: art,
    alt: "",
    style: {
      width: '100%',
      height: '100%',
      objectFit: 'cover',
      borderRadius: 4
    }
  }) : /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--holt-font-mono)',
      fontSize: 9,
      color: 'var(--holt-ink-42)'
    }
  }, "poster art")), title && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 11.5,
      fontWeight: 700,
      color: 'var(--holt-ink)',
      marginTop: 8,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, title), meta && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--holt-font-mono)',
      fontSize: 9.5,
      color: 'var(--holt-ink-42)',
      marginTop: 3
    }
  }, meta));
}
Object.assign(__ds_scope, { MediaTile });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/MediaTile/MediaTile.jsx", error: String((e && e.message) || e) }); }

// components/OtterMark/OtterMark.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const U = {
  w: 180,
  h: 150
};
function Eye({
  x,
  expression
}) {
  if (expression === 'idle') return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: 50,
      width: 22,
      height: 5,
      borderRadius: 3,
      background: 'var(--holt-deep)'
    }
  });
  return /*#__PURE__*/React.createElement(React.Fragment, null, expression === 'alert' && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x - 5,
      top: 36,
      width: 32,
      height: 32,
      borderRadius: '50%',
      border: '3px solid var(--holt-warning)',
      boxSizing: 'border-box'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x,
      top: 41,
      width: 22,
      height: 22,
      borderRadius: '50%',
      background: 'var(--holt-deep)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: x + 9,
      top: expression === 'alert' ? 43 : 45,
      width: 8,
      height: 8,
      borderRadius: '50%',
      background: '#fff'
    }
  }));
}

/** The full otter head, built from circles, one squashed ellipse and rounded rects. */
function OtterMark({
  size = 140,
  expression = 'happy',
  style,
  ...rest
}) {
  const scale = size / U.w;
  const whisker = (left, top, w, rot) => ({
    position: 'absolute',
    left,
    top,
    width: w,
    height: 3,
    borderRadius: 2,
    background: 'var(--holt-lilac)',
    transform: 'rotate(' + rot + 'deg)'
  });
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      position: 'relative',
      width: size,
      height: size * U.h / U.w,
      flex: 'none',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 0,
      top: 0,
      width: U.w,
      height: U.h,
      transform: 'scale(' + scale + ')',
      transformOrigin: 'top left'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 2,
      top: 30,
      width: 30,
      height: 25,
      borderRadius: '50%',
      background: 'var(--holt-current-deep)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 148,
      top: 30,
      width: 30,
      height: 25,
      borderRadius: '50%',
      background: 'var(--holt-current-deep)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 6,
      top: 20,
      width: 168,
      height: 118,
      borderRadius: '46% 46% 30% 30%/56% 56% 38% 38%',
      background: 'var(--holt-current)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 6,
      top: 20,
      width: 168,
      height: 24,
      borderRadius: '46% 46% 50% 50%/92% 92% 22% 22%',
      background: 'var(--holt-current-deep)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 46,
      top: 31,
      width: 24,
      height: 5,
      borderRadius: 3,
      background: 'var(--holt-deep)',
      transform: 'rotate(-4deg)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 110,
      top: 31,
      width: 24,
      height: 5,
      borderRadius: 3,
      background: 'var(--holt-deep)',
      transform: 'rotate(4deg)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 38,
      top: 70,
      width: 58,
      height: 52,
      borderRadius: '50%',
      background: 'var(--holt-lilac)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 84,
      top: 70,
      width: 58,
      height: 52,
      borderRadius: '50%',
      background: 'var(--holt-lilac)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 78,
      top: 70,
      width: 24,
      height: 13,
      borderRadius: '7px 7px 11px 11px',
      background: 'var(--holt-deep)'
    }
  }), [[52, 80], [64, 88], [111, 80], [123, 88]].map(([l, t], i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      position: 'absolute',
      left: l,
      top: t,
      width: 5,
      height: 5,
      borderRadius: '50%',
      background: 'rgba(13,11,18,.3)'
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: whisker(2, 76, 38, -9)
  }), /*#__PURE__*/React.createElement("div", {
    style: whisker(0, 85, 40, 2)
  }), /*#__PURE__*/React.createElement("div", {
    style: whisker(4, 94, 36, 12)
  }), /*#__PURE__*/React.createElement("div", {
    style: whisker(140, 76, 38, 9)
  }), /*#__PURE__*/React.createElement("div", {
    style: whisker(140, 85, 40, -2)
  }), /*#__PURE__*/React.createElement("div", {
    style: whisker(140, 94, 36, -12)
  }), /*#__PURE__*/React.createElement(Eye, {
    x: 49,
    expression: expression
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 39,
      top: 64,
      width: 21,
      height: 10,
      borderRadius: '50%',
      background: 'rgba(255,122,190,.5)'
    }
  }), /*#__PURE__*/React.createElement(Eye, {
    x: 113,
    expression: expression
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      left: 103,
      top: 64,
      width: 21,
      height: 10,
      borderRadius: '50%',
      background: 'rgba(255,122,190,.5)'
    }
  })));
}
Object.assign(__ds_scope, { OtterMark });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/OtterMark/OtterMark.jsx", error: String((e && e.message) || e) }); }

// components/Panel/Panel.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** The surface container: mono eyebrow left, meta right, content below. */
function Panel({
  children,
  title,
  meta,
  tone = 'surface',
  padding = 17,
  style,
  ...rest
}) {
  const bg = tone === 'deep' ? 'var(--holt-deep)' : tone === 'raised' ? 'var(--holt-raised)' : 'var(--holt-surface)';
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      background: bg,
      border: '1px solid var(--holt-hairline)',
      borderRadius: 'var(--holt-radius-lg)',
      padding,
      boxSizing: 'border-box',
      ...style
    }
  }, rest), (title || meta) && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 12,
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--holt-font-mono)',
      fontSize: 9.5,
      letterSpacing: 1.6,
      color: 'var(--holt-ink-42)',
      textTransform: 'uppercase'
    }
  }, title), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--holt-font-mono)',
      fontSize: 9.5,
      color: 'var(--holt-ink-42)',
      flex: 'none'
    }
  }, meta)), children);
}
Object.assign(__ds_scope, { Panel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/Panel/Panel.jsx", error: String((e && e.message) || e) }); }

// components/PoolMeter/PoolMeter.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Storage ring: the mark's geometry doing real work. */
function PoolMeter({
  percent = 36,
  size = 64,
  tone = 'healthy',
  lines = [],
  style,
  ...rest
}) {
  const color = tone === 'warning' ? 'var(--holt-warning)' : tone === 'idle' ? 'var(--holt-ink-28)' : 'var(--holt-healthy)';
  const stroke = Math.max(4, Math.round(size * 0.17));
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 15,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      width: size,
      height: size,
      borderRadius: '50%',
      boxSizing: 'border-box',
      flex: 'none',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'conic-gradient(' + color + ' ' + percent + '%, rgba(255,255,255,.10) 0)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: size - stroke * 2,
      height: size - stroke * 2,
      borderRadius: '50%',
      background: 'var(--holt-surface)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'var(--holt-font-mono)',
      fontSize: Math.round(size * 0.19),
      fontWeight: 600,
      color: 'var(--holt-ink)'
    }
  }, percent, "%")), lines.length > 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--holt-font-mono)',
      fontSize: 10.5,
      color: 'var(--holt-ink-55)',
      lineHeight: 1.9,
      minWidth: 0
    }
  }, lines.map((l, i) => /*#__PURE__*/React.createElement("div", {
    key: i
  }, l))));
}
Object.assign(__ds_scope, { PoolMeter });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/PoolMeter/PoolMeter.jsx", error: String((e && e.message) || e) }); }

// components/ProgressRow/ProgressRow.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** A queue line: label, bar, percent. Purple = in motion. */
function ProgressRow({
  label,
  percent = 0,
  meta,
  tone = 'current',
  style,
  ...rest
}) {
  const color = tone === 'healthy' ? 'var(--holt-healthy)' : tone === 'warning' ? 'var(--holt-warning)' : 'var(--holt-current)';
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 7,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      justifyContent: 'space-between',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12.5,
      fontWeight: 700,
      color: 'var(--holt-ink)',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--holt-font-mono)',
      fontSize: 10,
      color: 'var(--holt-ink-42)',
      flex: 'none'
    }
  }, meta ?? percent + '%')), /*#__PURE__*/React.createElement("div", {
    style: {
      height: 5,
      borderRadius: 3,
      background: 'rgba(255,255,255,.09)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: Math.max(0, Math.min(100, percent)) + '%',
      height: '100%',
      borderRadius: 3,
      background: color
    }
  })));
}
Object.assign(__ds_scope, { ProgressRow });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/ProgressRow/ProgressRow.jsx", error: String((e && e.message) || e) }); }

// components/RingMark/RingMark.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** The reduced mark: the pool the otter curls around — also an eye, a lens, a platter. */
function RingMark({
  size = 44,
  color = 'var(--holt-current)',
  filled = false,
  style,
  ...rest
}) {
  const stroke = Math.max(2, Math.round(size * 0.25));
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      position: 'relative',
      width: size,
      height: size,
      flex: 'none',
      borderRadius: '50%',
      border: stroke + 'px solid ' + color,
      boxSizing: 'border-box',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      ...style
    }
  }, rest), filled && /*#__PURE__*/React.createElement("div", {
    style: {
      width: Math.round(size * 0.22),
      height: Math.round(size * 0.22),
      borderRadius: '50%',
      background: color
    }
  }));
}
Object.assign(__ds_scope, { RingMark });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/RingMark/RingMark.jsx", error: String((e && e.message) || e) }); }

// components/Lockup/Lockup.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** The wordmark with its mark. Otter above 38px, ring below. */
function Lockup({
  mark = 'otter',
  orientation = 'horizontal',
  size = 44,
  tagline,
  color = 'var(--holt-ink)',
  markColor = 'var(--holt-current)',
  style,
  ...rest
}) {
  const stacked = orientation === 'stacked';
  const glyph = mark === 'ring' ? /*#__PURE__*/React.createElement(__ds_scope.RingMark, {
    size: size,
    color: markColor
  }) : /*#__PURE__*/React.createElement(__ds_scope.OtterMark, {
    size: size * 1.15
  });
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      flexDirection: stacked ? 'column' : 'row',
      alignItems: 'center',
      gap: stacked ? 10 : 13,
      ...style
    }
  }, rest), glyph, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: stacked ? 'center' : 'flex-start',
      gap: 5
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--holt-font-core)',
      fontWeight: 900,
      fontSize: size * 0.55,
      letterSpacing: size * -0.027 + 'px',
      color,
      lineHeight: 1
    }
  }, "HoltOS"), tagline && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--holt-font-mono)',
      fontSize: 9,
      letterSpacing: 1.6,
      color: 'var(--holt-healthy)',
      textTransform: 'uppercase'
    }
  }, tagline)));
}
Object.assign(__ds_scope, { Lockup });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/Lockup/Lockup.jsx", error: String((e && e.message) || e) }); }

// components/SelectRow/SelectRow.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/** Setup-flow choice row: checkbox, plain-language title, mono path, status. */
function SelectRow({
  title,
  meta,
  status,
  selected = false,
  disabled = false,
  onClick,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    onClick: disabled ? undefined : onClick,
    style: {
      background: 'var(--holt-surface)',
      border: '1.5px solid ' + (selected ? 'var(--holt-current)' : 'var(--holt-hairline)'),
      borderRadius: 9,
      padding: '12px 14px',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      opacity: disabled ? .55 : 1,
      cursor: disabled ? 'default' : 'pointer',
      boxSizing: 'border-box',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 17,
      height: 17,
      borderRadius: 5,
      flex: 'none',
      boxSizing: 'border-box',
      border: selected ? 'none' : '1.5px solid var(--holt-ink-28)',
      background: selected ? 'var(--holt-current)' : 'transparent',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }
  }, selected && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 7,
      height: 7,
      borderRadius: 2,
      background: 'var(--holt-deep)'
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      fontWeight: 700,
      color: 'var(--holt-ink)'
    }
  }, title), meta && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--holt-font-mono)',
      fontSize: 10,
      color: 'var(--holt-ink-42)',
      marginTop: 2
    }
  }, meta)), status && /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 'none'
    }
  }, status));
}
Object.assign(__ds_scope, { SelectRow });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/SelectRow/SelectRow.jsx", error: String((e && e.message) || e) }); }

// components/ServiceIcon/ServiceIcon.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const P = 'var(--holt-current)',
  T = 'var(--holt-healthy)',
  W = 'var(--holt-ink)';
const GLYPHS = {
  plex: {
    c: P,
    el: s => /*#__PURE__*/React.createElement("div", {
      style: {
        width: 0,
        height: 0,
        borderLeft: s * .42 + 'px solid ' + P,
        borderTop: s * .27 + 'px solid transparent',
        borderBottom: s * .27 + 'px solid transparent'
      }
    })
  },
  sonarr: {
    c: P,
    el: s => /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: s * .08
      }
    }, [.33, .54, .33].map((h, i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        width: s * .125,
        height: s * h,
        background: P,
        borderRadius: 2
      }
    })))
  },
  radarr: {
    c: P,
    el: s => /*#__PURE__*/React.createElement("div", {
      style: {
        width: s * .46,
        height: s * .46,
        background: P,
        transform: 'rotate(45deg)',
        borderRadius: 3
      }
    })
  },
  prowlarr: {
    c: P,
    el: s => /*#__PURE__*/React.createElement("div", {
      style: {
        width: s * .54,
        height: s * .54,
        borderRadius: '50%',
        border: s * .125 + 'px solid ' + P,
        boxSizing: 'border-box'
      }
    })
  },
  qbit: {
    c: T,
    el: s => /*#__PURE__*/React.createElement("div", {
      style: {
        width: 0,
        height: 0,
        borderTop: s * .4 + 'px solid ' + T,
        borderLeft: s * .27 + 'px solid transparent',
        borderRight: s * .27 + 'px solid transparent'
      }
    })
  },
  zfs: {
    c: T,
    el: s => /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: s * .08
      }
    }, [1, .6, .3].map((o, i) => /*#__PURE__*/React.createElement("div", {
      key: i,
      style: {
        width: s * .54,
        height: s * .125,
        background: T,
        opacity: o,
        borderRadius: 2
      }
    })))
  },
  podman: {
    c: W,
    el: s => /*#__PURE__*/React.createElement("div", {
      style: {
        width: s * .5,
        height: s * .5,
        border: s * .125 + 'px solid ' + W,
        boxSizing: 'border-box',
        borderRadius: 4
      }
    })
  },
  plasma: {
    c: W,
    el: s => /*#__PURE__*/React.createElement("div", {
      style: {
        width: s * .5,
        height: s * .5,
        borderRadius: '50%',
        background: W
      }
    })
  }
};

/** One geometric primitive per service. Purple = media pipeline, teal = storage & transfer, white = system. */
function ServiceIcon({
  service = 'plex',
  size = 48,
  label,
  style,
  ...rest
}) {
  const g = GLYPHS[service] || GLYPHS.plex;
  const tile = /*#__PURE__*/React.createElement("div", {
    style: {
      width: size,
      height: size,
      borderRadius: Math.round(size * 0.29),
      background: 'var(--holt-surface)',
      border: '1px solid rgba(255,255,255,.07)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flex: 'none',
      boxSizing: 'border-box'
    }
  }, g.el(size));
  if (!label) return /*#__PURE__*/React.createElement("div", _extends({
    style: style
  }, rest), tile);
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      gap: 9,
      ...style
    }
  }, rest), tile, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--holt-font-mono)',
      fontSize: 9.5,
      color: 'var(--holt-ink-42)'
    }
  }, label));
}
Object.assign(__ds_scope, { ServiceIcon });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/ServiceIcon/ServiceIcon.jsx", error: String((e && e.message) || e) }); }

// components/StatusPill/StatusPill.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const TONES = {
  healthy: {
    color: 'var(--holt-healthy)',
    dot: 'var(--holt-healthy)'
  },
  working: {
    color: 'var(--holt-current)',
    dot: 'var(--holt-current)'
  },
  warning: {
    color: 'var(--holt-warning)',
    dot: 'var(--holt-warning)'
  },
  idle: {
    color: 'var(--holt-ink-42)',
    dot: 'var(--holt-ink-28)'
  }
};

/** Teal only ever means online / healthy — never decoration. */
function StatusPill({
  children,
  tone = 'healthy',
  solid = false,
  style,
  ...rest
}) {
  const t = TONES[tone];
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      fontFamily: 'var(--holt-font-mono)',
      fontSize: 10.5,
      lineHeight: 1,
      padding: solid ? '6px 11px' : 0,
      borderRadius: 'var(--holt-radius-pill)',
      background: solid ? 'var(--holt-surface)' : 'transparent',
      color: t.color,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 6,
      height: 6,
      borderRadius: '50%',
      background: t.dot,
      flex: 'none'
    }
  }), children);
}
Object.assign(__ds_scope, { StatusPill });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/StatusPill/StatusPill.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Lockup = __ds_scope.Lockup;

__ds_ns.MediaTile = __ds_scope.MediaTile;

__ds_ns.OtterMark = __ds_scope.OtterMark;

__ds_ns.Panel = __ds_scope.Panel;

__ds_ns.PoolMeter = __ds_scope.PoolMeter;

__ds_ns.ProgressRow = __ds_scope.ProgressRow;

__ds_ns.RingMark = __ds_scope.RingMark;

__ds_ns.SelectRow = __ds_scope.SelectRow;

__ds_ns.ServiceIcon = __ds_scope.ServiceIcon;

__ds_ns.StatusPill = __ds_scope.StatusPill;

})();
