const P='var(--holt-current)', T='var(--holt-healthy)', W='var(--holt-ink)';
const GLYPHS={
  plex:{c:P,el:s=><div style={{width:0,height:0,borderLeft:(s*.42)+'px solid '+P,borderTop:(s*.27)+'px solid transparent',borderBottom:(s*.27)+'px solid transparent'}} />},
  sonarr:{c:P,el:s=><div style={{display:'flex',alignItems:'center',gap:s*.08}}>{[.33,.54,.33].map((h,i)=><div key={i} style={{width:s*.125,height:s*h,background:P,borderRadius:2}} />)}</div>},
  radarr:{c:P,el:s=><div style={{width:s*.46,height:s*.46,background:P,transform:'rotate(45deg)',borderRadius:3}} />},
  prowlarr:{c:P,el:s=><div style={{width:s*.54,height:s*.54,borderRadius:'50%',border:(s*.125)+'px solid '+P,boxSizing:'border-box'}} />},
  qbit:{c:T,el:s=><div style={{width:0,height:0,borderTop:(s*.4)+'px solid '+T,borderLeft:(s*.27)+'px solid transparent',borderRight:(s*.27)+'px solid transparent'}} />},
  zfs:{c:T,el:s=><div style={{display:'flex',flexDirection:'column',gap:s*.08}}>{[1,.6,.3].map((o,i)=><div key={i} style={{width:s*.54,height:s*.125,background:T,opacity:o,borderRadius:2}} />)}</div>},
  podman:{c:W,el:s=><div style={{width:s*.5,height:s*.5,border:(s*.125)+'px solid '+W,boxSizing:'border-box',borderRadius:4}} />},
  plasma:{c:W,el:s=><div style={{width:s*.5,height:s*.5,borderRadius:'50%',background:W}} />}
};

/** One geometric primitive per service. Purple = media pipeline, teal = storage & transfer, white = system. */
export function ServiceIcon({service='plex',size=48,label,style,...rest}){
  const g=GLYPHS[service]||GLYPHS.plex;
  const tile=(
    <div style={{width:size,height:size,borderRadius:Math.round(size*0.29),background:'var(--holt-surface)',border:'1px solid rgba(255,255,255,.07)',display:'flex',alignItems:'center',justifyContent:'center',flex:'none',boxSizing:'border-box'}}>{g.el(size)}</div>
  );
  if(!label) return <div style={style} {...rest}>{tile}</div>;
  return (
    <div style={{display:'flex',flexDirection:'column',alignItems:'center',gap:9,...style}} {...rest}>
      {tile}
      <div style={{fontFamily:'var(--holt-font-mono)',fontSize:9.5,color:'var(--holt-ink-42)'}}>{label}</div>
    </div>
  );
}
