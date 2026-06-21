export function imageUrl(filepath: string | null | undefined): string | null {
  if (!filepath) return null;
  if (filepath.startsWith('data:')) return filepath;
  if (filepath.startsWith('http')) return filepath;
  
  // Extract filename safely handling both backslashes and forward slashes
  const filename = filepath.replace(/\\/g, '/').split('/').pop();
  return `http://localhost:8001/generated/${filename}`;
}
