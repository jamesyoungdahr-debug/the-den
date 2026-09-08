const TONES={
  healthy:{color:'var(--holt-healthy)',dot:'var(--holt-healthy)'},
  working:{color:'var(--holt-current)',dot:'var(--holt-current)'},
  warning:{color:'var(--holt-warning)',dot:'var(--holt-warning)'},
  idle:{color:'var(--holt-ink-42)',dot:'var(--holt-ink-28)'}
};

/** Teal only ever means online / healthy — never decoration. */
export function StatusPill({children,tone='healthy',solid=false,style,...rest}){
  const t=TONES[tone];
  return (
    <span style={{display:'inline-flex',alignItems:'center',gap:6,fontFamily:'var(--holt-font-mono)',fontSize:10.5,lineHeight:1,padding:solid?'6px 11px':0,borderRadius:'var(--holt-radius-pill)',background:solid?'var(--holt-surface)':'transparent',color:t.color,...style}} {...rest}>
      <span style={{width:6,height:6,borderRadius:'50%',background:t.dot,flex:'none'}} />{children}
    </span>
  );
}
