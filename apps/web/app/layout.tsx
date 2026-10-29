import './style.css';
export const metadata = {title: 'GSN AI Video Studio', description: 'Your production workspace'};
export default function Layout({children}: {children: React.ReactNode}) {
  return <html lang="en"><body>{children}</body></html>;
}
