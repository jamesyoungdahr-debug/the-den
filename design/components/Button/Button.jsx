const SIZES={sm:{padding:'8px 14px',fontSize:12},md:{padding:'10px 20px',fontSize:12.5},lg:{padding:'13px 26px',fontSize:15}};
const VARIANTS={
  primary:{background:'var(--holt-current)',color:'var(--holt-deep)',fontWeight:800,borderColor:'transparent'},
  secondary:{background:'transparent',color:'var(--holt-ink-70)',fontWeight:700,borderColor:'var(--holt-hairline-strong)'},
  quiet:{background:'transparent',color:'var(--holt-ink-55)',fontWeight:700,borderColor:'transparent'},
  onCurrent:{background:'var(--holt-deep)',color:'var(--holt-ink)',fontWeight:800,borderColor:'transparent'}
};

export function Button({children,variant='primary',size='md',disabled=false,onClick,style,...rest}){
  const s={
    display:'inline-flex',alignItems:'center',justifyContent:'center',gap:8,
    fontFamily:'var(--holt-font-core)',letterSpacing:'-.2px',lineHeight:1,
    borderRadius:'var(--holt-radius-sm)',borderWidth:1,borderStyle:'solid',
    cursor:disabled?'default':'pointer',opacity:disabled?.4:1,
    transition:'filter .12s ease, background .12s ease',
    ...SIZES[size],...VARIANTS[variant],...style
  };
  return <button type="button" style={s} disabled={disabled} onClick={onClick} {...rest}>{children}</button>;
}
