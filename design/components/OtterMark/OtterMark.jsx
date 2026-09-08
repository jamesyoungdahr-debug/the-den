const U = {w:180,h:150};
function Eye({x, expression}){
  if(expression==='idle') return <div style={{position:'absolute',left:x,top:50,width:22,height:5,borderRadius:3,background:'var(--holt-deep)'}} />;
  return <>
    {expression==='alert' && <div style={{position:'absolute',left:x-5,top:36,width:32,height:32,borderRadius:'50%',border:'3px solid var(--holt-warning)',boxSizing:'border-box'}} />}
    <div style={{position:'absolute',left:x,top:41,width:22,height:22,borderRadius:'50%',background:'var(--holt-deep)'}} />
    <div style={{position:'absolute',left:x+9,top:expression==='alert'?43:45,width:8,height:8,borderRadius:'50%',background:'#fff'}} />
  </>;
}

/** The full otter head, built from circles, one squashed ellipse and rounded rects. */
export function OtterMark({size=140,expression='happy',style,...rest}){
  const scale = size/U.w;
  const whisker=(left,top,w,rot)=>({position:'absolute',left,top,width:w,height:3,borderRadius:2,background:'var(--holt-lilac)',transform:'rotate('+rot+'deg)'});
  return (
    <div style={{position:'relative',width:size,height:size*U.h/U.w,flex:'none',...style}} {...rest}>
      <div style={{position:'absolute',left:0,top:0,width:U.w,height:U.h,transform:'scale('+scale+')',transformOrigin:'top left'}}>
        <div style={{position:'absolute',left:2,top:30,width:30,height:25,borderRadius:'50%',background:'var(--holt-current-deep)'}} />
        <div style={{position:'absolute',left:148,top:30,width:30,height:25,borderRadius:'50%',background:'var(--holt-current-deep)'}} />
        <div style={{position:'absolute',left:6,top:20,width:168,height:118,borderRadius:'46% 46% 30% 30%/56% 56% 38% 38%',background:'var(--holt-current)'}} />
        <div style={{position:'absolute',left:6,top:20,width:168,height:24,borderRadius:'46% 46% 50% 50%/92% 92% 22% 22%',background:'var(--holt-current-deep)'}} />
        <div style={{position:'absolute',left:46,top:31,width:24,height:5,borderRadius:3,background:'var(--holt-deep)',transform:'rotate(-4deg)'}} />
        <div style={{position:'absolute',left:110,top:31,width:24,height:5,borderRadius:3,background:'var(--holt-deep)',transform:'rotate(4deg)'}} />
        <div style={{position:'absolute',left:38,top:70,width:58,height:52,borderRadius:'50%',background:'var(--holt-lilac)'}} />
        <div style={{position:'absolute',left:84,top:70,width:58,height:52,borderRadius:'50%',background:'var(--holt-lilac)'}} />
        <div style={{position:'absolute',left:78,top:70,width:24,height:13,borderRadius:'7px 7px 11px 11px',background:'var(--holt-deep)'}} />
        {[[52,80],[64,88],[111,80],[123,88]].map(([l,t],i)=>(
          <div key={i} style={{position:'absolute',left:l,top:t,width:5,height:5,borderRadius:'50%',background:'rgba(13,11,18,.3)'}} />
        ))}
        <div style={whisker(2,76,38,-9)} /><div style={whisker(0,85,40,2)} /><div style={whisker(4,94,36,12)} />
        <div style={whisker(140,76,38,9)} /><div style={whisker(140,85,40,-2)} /><div style={whisker(140,94,36,-12)} />
        <Eye x={49} expression={expression} />
        <div style={{position:'absolute',left:39,top:64,width:21,height:10,borderRadius:'50%',background:'rgba(255,122,190,.5)'}} />
        <Eye x={113} expression={expression} />
        <div style={{position:'absolute',left:103,top:64,width:21,height:10,borderRadius:'50%',background:'rgba(255,122,190,.5)'}} />
      </div>
    </div>
  );
}
