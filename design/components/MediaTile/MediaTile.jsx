/** Poster slot. Art is never invented — the striped ground stands in until real art lands. */
export function MediaTile({title,meta,width=86,ratio=1.48,tone='current',art,style,...rest}){
  const stripe = tone==='healthy' ? 'rgba(40,224,200,.24)' : 'rgba(177,77,255,.24)';
  return (
    <div style={{width,flex:'none',...style}} {...rest}>
      <div style={{width:'100%',height:width*ratio,borderRadius:6,background:'var(--holt-raised)',backgroundImage:art?undefined:'repeating-linear-gradient(135deg,'+stripe+' 0 6px,transparent 6px 13px)',display:'flex',alignItems:'flex-end',padding:8,boxSizing:'border-box',overflow:'hidden'}}>
        {art
          ? <img src={art} alt="" style={{width:'100%',height:'100%',objectFit:'cover',borderRadius:4}} />
          : <div style={{fontFamily:'var(--holt-font-mono)',fontSize:9,color:'var(--holt-ink-42)'}}>poster art</div>}
      </div>
      {title && <div style={{fontSize:11.5,fontWeight:700,color:'var(--holt-ink)',marginTop:8,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{title}</div>}
      {meta && <div style={{fontFamily:'var(--holt-font-mono)',fontSize:9.5,color:'var(--holt-ink-42)',marginTop:3}}>{meta}</div>}
    </div>
  );
}
