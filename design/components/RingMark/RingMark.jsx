/** The reduced mark: the pool the otter curls around — also an eye, a lens, a platter. */
export function RingMark({size=44,color='var(--holt-current)',filled=false,style,...rest}){
  const stroke = Math.max(2,Math.round(size*0.25));
  return (
    <div style={{position:'relative',width:size,height:size,flex:'none',borderRadius:'50%',border:stroke+'px solid '+color,boxSizing:'border-box',display:'flex',alignItems:'center',justifyContent:'center',...style}} {...rest}>
      {filled && <div style={{width:Math.round(size*0.22),height:Math.round(size*0.22),borderRadius:'50%',background:color}} />}
    </div>
  );
}
