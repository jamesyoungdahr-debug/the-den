import { OtterMark } from '../OtterMark/OtterMark.jsx';
import { RingMark } from '../RingMark/RingMark.jsx';

/** The wordmark with its mark. Otter above 38px, ring below. */
export function Lockup({mark='otter',orientation='horizontal',size=44,tagline,color='var(--holt-ink)',markColor='var(--holt-current)',style,...rest}){
  const stacked = orientation==='stacked';
  const glyph = mark==='ring'
    ? <RingMark size={size} color={markColor} />
    : <OtterMark size={size*1.15} />;
  return (
    <div style={{display:'flex',flexDirection:stacked?'column':'row',alignItems:'center',gap:stacked?10:13,...style}} {...rest}>
      {glyph}
      <div style={{display:'flex',flexDirection:'column',alignItems:stacked?'center':'flex-start',gap:5}}>
        <div style={{fontFamily:'var(--holt-font-core)',fontWeight:900,fontSize:size*0.55,letterSpacing:size*-0.027+'px',color,lineHeight:1}}>HoltOS</div>
        {tagline && <div style={{fontFamily:'var(--holt-font-mono)',fontSize:9,letterSpacing:1.6,color:'var(--holt-healthy)',textTransform:'uppercase'}}>{tagline}</div>}
      </div>
    </div>
  );
}
