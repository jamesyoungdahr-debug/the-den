/** Setup-flow choice row: checkbox, plain-language title, mono path, status. */
export function SelectRow({title,meta,status,selected=false,disabled=false,onClick,style,...rest}){
  return (
    <div onClick={disabled?undefined:onClick} style={{background:'var(--holt-surface)',border:'1.5px solid '+(selected?'var(--holt-current)':'var(--holt-hairline)'),borderRadius:9,padding:'12px 14px',display:'flex',alignItems:'center',gap:12,opacity:disabled?.55:1,cursor:disabled?'default':'pointer',boxSizing:'border-box',...style}} {...rest}>
      <div style={{width:17,height:17,borderRadius:5,flex:'none',boxSizing:'border-box',border:selected?'none':'1.5px solid var(--holt-ink-28)',background:selected?'var(--holt-current)':'transparent',display:'flex',alignItems:'center',justifyContent:'center'}}>
        {selected && <div style={{width:7,height:7,borderRadius:2,background:'var(--holt-deep)'}} />}
      </div>
      <div style={{flex:1,minWidth:0}}>
        <div style={{fontSize:13,fontWeight:700,color:'var(--holt-ink)'}}>{title}</div>
        {meta && <div style={{fontFamily:'var(--holt-font-mono)',fontSize:10,color:'var(--holt-ink-42)',marginTop:2}}>{meta}</div>}
      </div>
      {status && <div style={{flex:'none'}}>{status}</div>}
    </div>
  );
}
