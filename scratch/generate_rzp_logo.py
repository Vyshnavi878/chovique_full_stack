from PIL import Image
import base64, io, os

img_path = r'c:\Users\PBV Avinash\OneDrive\Desktop\Chovique_APPs\Chovique_TEST\chovique_full_stack_frontend\public\assets\popular-bg.jpg'
img = Image.open(img_path)

# Crop square centered on the royal wolf crest and CHOVIQUE text
# In 1024x1024, wolf crest top is ~150, text bottom is ~680. Center is ~(512, 420)
crop_square = img.crop((182, 140, 842, 800))
crop_square.thumbnail((160, 160), Image.Resampling.LANCZOS)

buf = io.BytesIO()
crop_square.save(buf, format='JPEG', quality=85)
b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
data_url = f'data:image/jpeg;base64,{b64}'
print('Length of data URL:', len(data_url))

out_dir = r'c:\Users\PBV Avinash\OneDrive\Desktop\Chovique_APPs\Chovique_TEST\chovique_full_stack_frontend\src\assets'
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, 'razorpayLogo.ts')
with open(out_file, 'w', encoding='utf-8') as f:
    f.write(f'export const RAZORPAY_CHOVIQUE_LOGO = "{data_url}";\n')

print(f'Successfully written to {out_file}!')
