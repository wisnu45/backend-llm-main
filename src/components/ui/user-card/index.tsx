interface Props {
  name: string;
  id: string;
  avatarSrc?: string;
}

function UserCard({ name, id, avatarSrc }: Props) {
  return (
    <div className="relative m-2 flex h-36 w-56 flex-col justify-between overflow-hidden rounded-xl bg-gray-600 p-4">
      <div className="flex items-center space-x-4">
        <img
          src={avatarSrc || `https://ui-avatars.com/api/?name=${name}`}
          alt="User Avatar"
          className="mt-2 h-10 w-10 rounded-lg object-cover"
        />
      </div>

      <div className="text-white">
        <h2 className="mb-1 text-lg font-semibold">{name}</h2>
        <p className="text-md opacity-75">{id}</p>
      </div>

      <div className="absolute bottom-[-50px] right-[-30px] h-32 w-32 rounded-full bg-white bg-opacity-10"></div>
      <div className="absolute bottom-[-60px] right-[60px] h-20 w-20 rounded-full bg-white bg-opacity-10"></div>
    </div>
  );
}

export default UserCard;
