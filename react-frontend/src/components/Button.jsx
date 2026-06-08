export default function Button({ variant='primary', className='', ...props }){
  const cls = variant === 'secondary' ? 'btn-secondary' : 'btn-primary';
  return <button className={`${cls} ${className}`} {...props} />;
}
