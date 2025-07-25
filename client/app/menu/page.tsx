'use client'

import { useSession, signOut } from 'next-auth/react';
import { Button } from '@/components/ui/button';

const Page = () => {
  const { data: session, status } = useSession();

  if (status === 'loading') return <p>Loading...</p>;

  if (status === 'unauthenticated') {
    return <h2 className='text-2xl'>Please login to see this menu page</h2>;
  }

  return (
    <div>
      <h2 className='text-2xl'>Menu page - welcome back {session?.user.username || session?.user.name}</h2>
      <Button variant='destructive' onClick={() => signOut()}>Sign Out</Button>
    </div>
  );
};

export default Page;
