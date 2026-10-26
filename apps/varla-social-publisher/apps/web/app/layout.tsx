import "./globals.css";
export const metadata={title:"Varla Social Publisher",description:"Local-first social publishing operations"};
export default function Layout({children}:{children:React.ReactNode}){return <html lang="en"><body><div className="shell"><aside className="side"><div className="brand">VARLA / Publisher</div><nav className="nav">{["Dashboard","Create Post","Content Calendar","Media Library","Accounts","Publishing Logs","Settings"].map(x=><a href="#" key={x}>{x}</a>)}</nav></aside>{children}</div></body></html>}
