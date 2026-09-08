/** The surface container: mono eyebrow left, meta right, content below. */
export function Panel({children,title,meta,tone='surface',padding=17,style,...rest}){
  const bg = tone==='deep' ? 'var(--holt-deep)' : tone==='raised' ? 'var(--holt-raised)' : 'var(--holt-surface)';
  return (
    <div style={{background:bg,border:'1px solid var(--holt-hairline)',borderRadius:'var(--holt-radius-lg)',padding,boxSizing:'border-box',...style}} {...rest}>
      {(title||meta) && (
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',gap:12,marginBottom:14}}>
          <div style={{fontFamily:'var(--holt-font-mono)',fontSize:9.5,letterSpacing:1.6,color:'var(--holt-ink-42)',textTransform:'uppercase'}}>{title}</div>
          <div style={{fontFamily:'var(--holt-font-mono)',fontSize:9.5,color:'var(--holt-ink-42)',flex:'none'}}>{meta}</div>
        </div>
      )}
      {children}
    </div>
  );
}
