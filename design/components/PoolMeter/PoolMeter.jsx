/** Storage ring: the mark's geometry doing real work. */
export function PoolMeter({percent=36,size=64,tone='healthy',lines=[],style,...rest}){
  const color = tone==='warning'?'var(--holt-warning)':tone==='idle'?'var(--holt-ink-28)':'var(--holt-healthy)';
  const stroke = Math.max(4,Math.round(size*0.17));
  return (
    <div style={{display:'flex',alignItems:'center',gap:15,...style}} {...rest}>
      <div style={{width:size,height:size,borderRadius:'50%',boxSizing:'border-box',flex:'none',display:'flex',alignItems:'center',justifyContent:'center',background:'conic-gradient('+color+' '+percent+'%, rgba(255,255,255,.10) 0)'}}>
        <div style={{width:size-stroke*2,height:size-stroke*2,borderRadius:'50%',background:'var(--holt-surface)',display:'flex',alignItems:'center',justifyContent:'center',fontFamily:'var(--holt-font-mono)',fontSize:Math.round(size*0.19),fontWeight:600,color:'var(--holt-ink)'}}>{percent}%</div>
      </div>
      {lines.length>0 && (
        <div style={{fontFamily:'var(--holt-font-mono)',fontSize:10.5,color:'var(--holt-ink-55)',lineHeight:1.9,minWidth:0}}>
          {lines.map((l,i)=><div key={i}>{l}</div>)}
        </div>
      )}
    </div>
  );
}
