/** A queue line: label, bar, percent. Purple = in motion. */
export function ProgressRow({label,percent=0,meta,tone='current',style,...rest}){
  const color = tone==='healthy'?'var(--holt-healthy)':tone==='warning'?'var(--holt-warning)':'var(--holt-current)';
  return (
    <div style={{display:'flex',flexDirection:'column',gap:7,...style}} {...rest}>
      <div style={{display:'flex',alignItems:'baseline',justifyContent:'space-between',gap:12}}>
        <div style={{fontSize:12.5,fontWeight:700,color:'var(--holt-ink)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{label}</div>
        <div style={{fontFamily:'var(--holt-font-mono)',fontSize:10,color:'var(--holt-ink-42)',flex:'none'}}>{meta ?? percent+'%'}</div>
      </div>
      <div style={{height:5,borderRadius:3,background:'rgba(255,255,255,.09)',overflow:'hidden'}}>
        <div style={{width:Math.max(0,Math.min(100,percent))+'%',height:'100%',borderRadius:3,background:color}} />
      </div>
    </div>
  );
}
